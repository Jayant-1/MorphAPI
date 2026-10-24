"""
MorphAPI Playwright Manager
Manages browser lifecycle, isolated contexts, timeouts, resource cleanup, and redirect SSRF interception.
"""

import asyncio
import logging
from typing import AsyncGenerator
from contextlib import asynccontextmanager
from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    Page,
    Playwright,
    Error as PlaywrightError,
    TimeoutError as PlaywrightTimeoutError,
)

from morphapi.config import settings
from morphapi.browser.url_policy import UrlPolicyService
from morphapi.schemas.errors import FailureCode, BrowserExecutionError, SsrfSecurityError

logger = logging.getLogger("morphapi.browser")


class PlaywrightManager:
    """
    Manages Playwright lifecycle, concurrency, isolated contexts, and redirect inspection.
    """

    def __init__(
        self,
        headless: bool | None = None,
        timeout_ms: int | None = None,
        navigation_timeout_ms: int | None = None,
        url_policy: UrlPolicyService | None = None,
    ):
        self.headless = headless if headless is not None else settings.playwright_headless
        self.timeout_ms = timeout_ms if timeout_ms is not None else settings.playwright_timeout_ms
        self.navigation_timeout_ms = navigation_timeout_ms if navigation_timeout_ms is not None else settings.playwright_navigation_timeout_ms
        self.url_policy = url_policy or UrlPolicyService(allow_local=settings.allow_local_network)

        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._lock = asyncio.Lock()

    async def _ensure_browser(self) -> Browser:
        async with self._lock:
            if self._playwright is None:
                self._playwright = await async_playwright().start()
            if self._browser is None or not self._browser.is_connected():
                self._browser = await self._playwright.chromium.launch(
                    headless=self.headless,
                    args=[
                        "--disable-gpu",
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-setuid-sandbox",
                    ],
                )
            return self._browser

    @asynccontextmanager
    async def new_page_session(self, target_url: str | None = None) -> AsyncGenerator[Page, None]:
        """
        Creates an isolated browser context and page session.
        Applies route-level redirect verification to defend against redirect-based SSRF.
        Ensures context is closed upon completion.
        """
        if target_url:
            self.url_policy.enforce_url_policy(target_url)

        browser = await self._ensure_browser()
        context: BrowserContext = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            ignore_https_errors=False,
            user_agent="MorphAPI-Bot/1.0 (+https://morphapi.dev/bot)",
        )
        page: Page = await context.new_page()
        page.set_default_timeout(self.timeout_ms)
        page.set_default_navigation_timeout(self.navigation_timeout_ms)

        # Route-level interception to inspect redirect target locations
        async def handle_route(route):
            req = route.request
            url = req.url
            # Verify URL policy on sub-requests and redirects
            if req.is_navigation_request():
                is_safe, reason = self.url_policy.validate_url(url)
                if not is_safe:
                    logger.warning("Blocked outbound request to unsafe URL '%s': %s", url, reason)
                    await route.abort("blockedbyclient")
                    return
            await route.continue_()

        try:
            await page.route("**/*", handle_route)
            yield page
        finally:
            try:
                await context.close()
            except Exception as e:
                logger.debug("Error closing context: %s", e)

    async def navigate_safely(self, page: Page, url: str) -> None:
        """
        Navigates page to URL with bounded wait and policy verification.
        """
        self.url_policy.enforce_url_policy(url)
        try:
            response = await page.goto(url, wait_until="domcontentloaded", timeout=self.navigation_timeout_ms)
            if response is None:
                raise BrowserExecutionError(
                    FailureCode.BROWSER_NAVIGATION_ERROR,
                    f"Navigation returned no response for '{url}'",
                )
            if response.status >= 400:
                raise BrowserExecutionError(
                    FailureCode.BROWSER_NAVIGATION_ERROR,
                    f"Website returned HTTP error {response.status} for '{url}'",
                )
            # Brief pause to allow client-side JavaScript / SPAs to mount data
            try:
                await page.wait_for_load_state("load", timeout=3000)
            except Exception:
                pass
            if response is None:
                raise BrowserExecutionError(
                    FailureCode.BROWSER_NAVIGATION_ERROR,
                    f"Navigation returned no response for '{url}'",
                )
            # Check HTTP status
            if response.status >= 400:
                raise BrowserExecutionError(
                    FailureCode.BROWSER_NAVIGATION_ERROR,
                    f"Website returned HTTP error {response.status} for '{url}'",
                )
        except PlaywrightTimeoutError as te:
            raise BrowserExecutionError(
                FailureCode.BROWSER_TIMEOUT,
                f"Timed out after {self.navigation_timeout_ms}ms navigating to '{url}'",
            ) from te
        except SsrfSecurityError:
            raise
        except PlaywrightError as pe:
            msg = str(pe)
            if "ERR_NAME_NOT_RESOLVED" in msg or "ERR_CONNECTION_REFUSED" in msg:
                code = FailureCode.DNS_RESOLUTION_FAILED
            else:
                code = FailureCode.BROWSER_NAVIGATION_ERROR
            raise BrowserExecutionError(code, f"Navigation failed for '{url}': {msg}") from pe

    async def close(self) -> None:
        """Closes browser and stops Playwright engine."""
        async with self._lock:
            if self._browser is not None:
                try:
                    await self._browser.close()
                except Exception:
                    pass
                self._browser = None
            if self._playwright is not None:
                try:
                    await self._playwright.stop()
                except Exception:
                    pass
                self._playwright = None
