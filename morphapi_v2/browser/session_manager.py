"""
Playwright Browser Session Manager for MorphAPI V2
Provides realistic browser environments, anti-bot evasion headers, and DOM stabilization.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from morphapi_v2.config import settings

logger = logging.getLogger("morphapi_v2.browser")


class BrowserSessionManagerV2:
    def __init__(self):
        self._playwright = None
        self._browser: Browser | None = None
        self._lock = asyncio.Lock()

    async def _ensure_browser(self) -> Browser:
        async with self._lock:
            if self._playwright is None:
                self._playwright = await async_playwright().start()
            if self._browser is None or not self._browser.is_connected():
                self._browser = await self._playwright.chromium.launch(
                    headless=settings.playwright_headless,
                    args=[
                        "--disable-gpu",
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-setuid-sandbox",
                        "--disable-blink-features=AutomationControlled",
                    ],
                )
            return self._browser

    @asynccontextmanager
    async def new_page_session(self) -> AsyncGenerator[Page, None]:
        browser = await self._ensure_browser()
        context: BrowserContext = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=settings.user_agent,
            locale="en-US",
            timezone_id="America/New_York",
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1",
            },
        )
        page: Page = await context.new_page()
        page.set_default_timeout(settings.playwright_timeout_ms)
        page.set_default_navigation_timeout(settings.navigation_timeout_ms)

        try:
            yield page
        finally:
            try:
                if not page.is_closed():
                    await page.close()
                await context.close()
            except Exception as e:
                logger.debug("Error closing page/context: %s", e)

    async def navigate_and_stabilize(self, page: Page, url: str) -> None:
        """
        Navigates to URL and waits for page to stabilize:
        1. Loads DOM (domcontentloaded).
        2. Tries to wait for networkidle (bounded by 8s).
        3. Waits for DOM node count mutation stability.
        """
        logger.info("[BrowserSessionManagerV2] Navigating to '%s'", url)
        # Step 1: DOM content loaded
        await page.goto(url, wait_until="domcontentloaded", timeout=settings.navigation_timeout_ms)

        # Step 2: Bounded networkidle wait
        try:
            await page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            # Many modern SPAs have persistent websockets or telemetry; don't fail if networkidle times out
            pass

        # Step 3: Wait for DOM stabilization (element count stops fluctuating)
        try:
            await page.evaluate("""() => {
                return new Promise(resolve => {
                    let lastCount = document.body ? document.body.querySelectorAll('*').length : 0;
                    let stableTicks = 0;
                    const interval = setInterval(() => {
                        const currentCount = document.body ? document.body.querySelectorAll('*').length : 0;
                        if (currentCount === lastCount && currentCount > 20) {
                            stableTicks++;
                            if (stableTicks >= 2) {
                                clearInterval(interval);
                                resolve(currentCount);
                            }
                        } else {
                            stableTicks = 0;
                            lastCount = currentCount;
                        }
                    }, 250);
                    setTimeout(() => {
                        clearInterval(interval);
                        resolve(lastCount);
                    }, 4000);
                });
            }""")
        except Exception as e:
            logger.debug("DOM stabilization check completed with fallback: %s", e)

    async def close(self):
        async with self._lock:
            if self._browser:
                try:
                    await self._browser.close()
                except Exception:
                    pass
                self._browser = None
            if self._playwright:
                try:
                    await self._playwright.stop()
                except Exception:
                    pass
                self._playwright = None


session_manager_v2 = BrowserSessionManagerV2()
