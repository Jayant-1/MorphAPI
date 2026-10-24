"""
MorphAPI Playwright Extraction Service
Reusable, high-performance web extraction engine using Playwright.
Executes saved or discovered selectors directly against the live DOM.
Uses deterministic normalization and strict schema validation.
Fast path never invokes LLMs or fabricates missing values.
"""

import asyncio
import os
import time
from datetime import datetime, timezone
from typing import Any
from playwright.async_api import (
    async_playwright,
    Browser,
    Page,
    Route,
    Request,
    TimeoutError as PlaywrightTimeoutError,
)

from backend.app.models.contracts import (
    ExtractionDiagnostics,
    ExtractionResult,
    FieldExtractionDiagnostic,
)
from backend.app.services.security import (
    validate_url_ssrf,
    validate_redirect_url,
    validate_selector_safety,
    SecurityValidationError,
)
from backend.app.services.validator import validate_and_normalize_dataset


class PlaywrightExtractionService:
    """
    Service responsible for opening target URLs and executing selector queries.
    """

    def __init__(
        self,
        timeout_ms: int | None = None,
        headless: bool | None = None,
        allow_local: bool | None = None,
    ):
        self.timeout_ms = timeout_ms or int(os.getenv("PLAYWRIGHT_TIMEOUT_MS", "8000"))
        self.headless = (
            headless
            if headless is not None
            else os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() in ("true", "1")
        )
        self.allow_local = (
            allow_local
            if allow_local is not None
            else os.getenv("ALLOW_LOCAL_TARGETS", "false").lower() in ("true", "1")
        )
        self._browser: Browser | None = None
        self._playwright = None
        self._lock = asyncio.Lock()

    async def _get_browser(self) -> Browser:
        async with self._lock:
            if self._browser is None or not self._browser.is_connected():
                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(
                    headless=self.headless,
                    args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
                )
            return self._browser

    async def close(self):
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

    async def extract_data(
        self,
        target_url: str,
        selectors: dict[str, str],
        schema_definition: dict[str, str],
        request_context: dict[str, Any] | None = None,
    ) -> ExtractionResult:
        """Alias for extract() supporting flexible argument orders for orchestrator."""
        return await self.extract(
            target_url=target_url,
            schema_definition=schema_definition,
            selectors=selectors,
            request_context=request_context,
        )

    async def capture_context(self, target_url: str) -> dict[str, Any]:
        """
        Captures title, raw HTML, and screenshot for LangGraph healing inspection.
        """
        browser = await self._get_browser()
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="MorphAPI-Extractor/1.0 (+https://github.com/Jayant-1/MorphAPI)",
        )
        page = await context.new_page()
        try:
            await page.goto(target_url, timeout=self.timeout_ms, wait_until="domcontentloaded")
            title = await page.title()
            html = await page.content()
            screenshot_bytes = await page.screenshot(type="png", full_page=False)
            import base64
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode("ascii")
            return {
                "title": title,
                "html": html,
                "screenshot_b64": screenshot_b64,
            }
        finally:
            await context.close()

    async def extract(
        self,
        target_url: str,
        schema_definition: dict[str, str],
        selectors: dict[str, str],
        request_context: dict[str, Any] | None = None,
    ) -> ExtractionResult:
        """
        Executes selector-based extraction against the target URL.
        """
        start_time = time.perf_counter()
        started_at = datetime.now(timezone.utc).isoformat()
        field_diagnostics: list[FieldExtractionDiagnostic] = []
        errors: list[str] = []
        page_title: str | None = None

        # 1. SSRF and destination security validation
        is_safe_url, ssrf_err = validate_url_ssrf(target_url, allow_local=self.allow_local)
        if not is_safe_url:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            diag = ExtractionDiagnostics(
                target_url=target_url,
                started_at=started_at,
                finished_at=datetime.now(timezone.utc).isoformat(),
                latency_ms=latency_ms,
                field_diagnostics=[],
                page_title=None,
                errors=[f"Security policy violation: {ssrf_err}"],
            )
            return ExtractionResult(
                success=False,
                data=None,
                diagnostics=diag,
                error_code="SSRF_PROHIBITED",
                error_message=ssrf_err,
                is_schema_valid=False,
                validation_errors=[ssrf_err or "Restricted network destination"],
            )

        # 2. Selector safety validation
        for field, sel in selectors.items():
            is_safe_sel, sel_err = validate_selector_safety(sel)
            if not is_safe_sel:
                latency_ms = int((time.perf_counter() - start_time) * 1000)
                diag = ExtractionDiagnostics(
                    target_url=target_url,
                    started_at=started_at,
                    finished_at=datetime.now(timezone.utc).isoformat(),
                    latency_ms=latency_ms,
                    field_diagnostics=[],
                    page_title=None,
                    errors=[f"Unsafe selector for '{field}': {sel_err}"],
                )
                return ExtractionResult(
                    success=False,
                    data=None,
                    diagnostics=diag,
                    error_code="UNSAFE_SELECTOR",
                    error_message=f"Selector for field '{field}' rejected: {sel_err}",
                    is_schema_valid=False,
                    validation_errors=[f"Unsafe selector: {sel_err}"],
                )

        # 3. Launch browser page and attach redirect protections
        browser = await self._get_browser()
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="MorphAPI-Extractor/1.0 (+https://github.com/Jayant-1/MorphAPI)",
        )
        page = await context.new_page()

        # Intercept and validate redirect destinations to prevent redirect SSRF
        async def handle_route(route: Route, request: Request):
            req_url = request.url
            # Allow data / blob or check http(s)
            if req_url.startswith("http://") or req_url.startswith("https://"):
                safe, err = validate_url_ssrf(req_url, allow_local=self.allow_local)
                if not safe:
                    await route.abort("blockedbyclient")
                    return
            await route.continue_()

        await page.route("**/*", handle_route)

        try:
            # 4. Navigate with configured timeout
            await page.goto(
                target_url,
                timeout=self.timeout_ms,
                wait_until="domcontentloaded",
            )
            page_title = await page.title()

            # 5. Wait explicitly for at least one primary element if selectors provided
            primary_selector = next(iter(selectors.values()), None)
            if primary_selector:
                try:
                    await page.wait_for_selector(
                        primary_selector,
                        state="attached",
                        timeout=min(self.timeout_ms, 3000),
                    )
                except PlaywrightTimeoutError:
                    # Continue; field diagnostics will record the exact missing elements
                    pass

            # 6. Extract raw field values
            raw_field_matches: dict[str, list[str]] = {}
            for field_name, selector in selectors.items():
                try:
                    locator = page.locator(selector)
                    count = await locator.count()
                    values: list[str] = []
                    if count > 0:
                        for i in range(count):
                            el = locator.nth(i)
                            tag_name = await el.evaluate("el => el.tagName.toLowerCase()")
                            if tag_name in ("input", "textarea", "select"):
                                val = await el.input_value()
                            else:
                                val = await el.inner_text()
                            values.append(val.strip())
                    raw_field_matches[field_name] = values

                    field_diagnostics.append(
                        FieldExtractionDiagnostic(
                            field_name=field_name,
                            selector=selector,
                            matched_count=count,
                            raw_value=values[0] if count == 1 else (values if count > 1 else None),
                            error=None if count > 0 else f"Selector '{selector}' matched 0 elements",
                        )
                    )
                    if count == 0:
                        errors.append(f"Field '{field_name}' selector '{selector}' returned 0 elements")

                except Exception as ex:
                    errors.append(f"Error querying selector for '{field_name}': {ex}")
                    field_diagnostics.append(
                        FieldExtractionDiagnostic(
                            field_name=field_name,
                            selector=selector,
                            matched_count=0,
                            raw_value=None,
                            error=str(ex),
                        )
                    )

            # 7. Structure extracted data into records
            raw_dataset: Any = None
            if not errors:
                counts = [len(v) for v in raw_field_matches.values()]
                if not counts or all(c == 0 for c in counts):
                    errors.append("No elements matched any selector")
                elif all(c == 1 for c in counts):
                    # Single record
                    raw_dataset = {k: v[0] for k, v in raw_field_matches.items()}
                else:
                    # Multiple rows / items
                    # Check if all fields matched equal count
                    first_count = counts[0]
                    if all(c == first_count for c in counts):
                        dataset = []
                        for i in range(first_count):
                            row = {k: raw_field_matches[k][i] for k in raw_field_matches}
                            dataset.append(row)
                        raw_dataset = dataset
                    else:
                        errors.append(
                            f"Ambiguous element counts across fields: "
                            f"{ {k: len(v) for k, v in raw_field_matches.items()} }"
                        )

            # 8. Deterministic Normalization and Schema Validation
            is_valid = False
            normalized_data = None
            validation_errors = []

            if not errors and raw_dataset is not None:
                is_valid, normalized_data, validation_errors = validate_and_normalize_dataset(
                    raw_dataset, schema_definition
                )
                if not is_valid:
                    errors.extend(validation_errors)

            latency_ms = int((time.perf_counter() - start_time) * 1000)
            finished_at = datetime.now(timezone.utc).isoformat()

            diag = ExtractionDiagnostics(
                target_url=target_url,
                started_at=started_at,
                finished_at=finished_at,
                latency_ms=latency_ms,
                field_diagnostics=field_diagnostics,
                page_title=page_title,
                errors=errors,
            )

            success = is_valid and len(errors) == 0

            if success:
                err_code = None
            elif any("0 elements" in e or "selector" in e.lower() for e in errors):
                err_code = "SELECTOR_FAILED"
            elif not is_valid:
                err_code = "SCHEMA_VALIDATION_FAILED"
            else:
                err_code = "EXTRACTION_FAILED"

            return ExtractionResult(
                success=success,
                data=normalized_data if success else None,
                diagnostics=diag,
                error_code=err_code,
                error_message="; ".join(errors) if errors else None,
                is_schema_valid=is_valid,
                validation_errors=validation_errors,
            )

        except PlaywrightTimeoutError as e:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            err_msg = f"Navigation or selector timed out after {self.timeout_ms}ms: {e}"
            diag = ExtractionDiagnostics(
                target_url=target_url,
                started_at=started_at,
                finished_at=datetime.now(timezone.utc).isoformat(),
                latency_ms=latency_ms,
                field_diagnostics=field_diagnostics,
                page_title=page_title,
                errors=[err_msg],
            )
            return ExtractionResult(
                success=False,
                data=None,
                diagnostics=diag,
                error_code="TIMEOUT",
                error_message=err_msg,
                is_schema_valid=False,
                validation_errors=[err_msg],
            )

        except Exception as e:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            err_msg = f"Browser execution error: {e}"
            diag = ExtractionDiagnostics(
                target_url=target_url,
                started_at=started_at,
                finished_at=datetime.now(timezone.utc).isoformat(),
                latency_ms=latency_ms,
                field_diagnostics=field_diagnostics,
                page_title=page_title,
                errors=[err_msg],
            )
            return ExtractionResult(
                success=False,
                data=None,
                diagnostics=diag,
                error_code="BROWSER_ERROR",
                error_message=err_msg,
                is_schema_valid=False,
                validation_errors=[err_msg],
            )

        finally:
            await context.close()
