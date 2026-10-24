"""
MorphAPI Browser Extractor
Navigates isolated Playwright sessions, tests selectors, and extracts actual structured data.
"""

import logging
import time
from typing import Any
from playwright.async_api import Page

from morphapi.browser.playwright_manager import PlaywrightManager
from morphapi.browser.page_inspector import PageInspector, EvidenceStore
from morphapi.browser.selector_tester import SelectorTester
from morphapi.schemas.contracts import ExtractionResult, FieldEvidence
from morphapi.schemas.errors import FailureCode, BrowserExecutionError, MorphApiError

logger = logging.getLogger("morphapi.extractor")


class BrowserExtractor:
    """
    Extracts structured data from rendered pages using real Playwright browser sessions.
    """

    def __init__(
        self,
        manager: PlaywrightManager | None = None,
        inspector: PageInspector | None = None,
        tester: SelectorTester | None = None,
        evidence_store: EvidenceStore | None = None,
    ):
        self.manager = manager or PlaywrightManager()
        self.evidence_store = evidence_store or EvidenceStore()
        self.inspector = inspector or PageInspector(evidence_store=self.evidence_store)
        self.tester = tester or SelectorTester()

    async def extract_from_page(
        self,
        page: Page,
        endpoint_id: str,
        target_url: str,
        schema_definition: dict[str, str],
        selector_map: dict[str, str],
    ) -> ExtractionResult:
        """
        Extracts data using an already open, rendered Playwright page.
        """
        start_time = time.monotonic()
        try:
            # 1. Collect field evidence
            evidences = await self.tester.test_all_selectors(page, selector_map, max_samples=100)

            # 2. Check for missing or broken selectors
            missing_fields: list[str] = []
            for ev in evidences:
                if ev.matched_count == 0 or ev.error:
                    missing_fields.append(ev.field_name)

            if missing_fields:
                latency_ms = int((time.monotonic() - start_time) * 1000)
                return ExtractionResult(
                    success=False,
                    data=None,
                    field_evidences=evidences,
                    page_title=await page.title(),
                    target_url=target_url,
                    latency_ms=latency_ms,
                    error_code=FailureCode.SELECTOR_NOT_FOUND,
                    error_message=f"Selectors failed to match required fields: {', '.join(missing_fields)}",
                )

            # 3. Determine if dataset is a list of rows or a single record
            counts = [ev.matched_count for ev in evidences]
            is_list = len(counts) > 0 and all(c > 1 for c in counts)

            extracted_data: Any = None
            if is_list:
                # Repeated items: align by index
                min_rows = min(counts)
                dataset = []
                for row_idx in range(min_rows):
                    row: dict[str, Any] = {}
                    for ev in evidences:
                        val = ev.sample_values[row_idx] if row_idx < len(ev.sample_values) else None
                        row[ev.field_name] = val
                    dataset.append(row)
                extracted_data = dataset
            else:
                # Single record
                record: dict[str, Any] = {}
                for ev in evidences:
                    val = ev.sample_values[0] if ev.sample_values else None
                    record[ev.field_name] = val
                extracted_data = record

            # 4. Save evidence for audit trail
            inspection = await self.inspector.inspect(page, endpoint_id=endpoint_id, capture_screenshot=False)
            latency_ms = int((time.monotonic() - start_time) * 1000)

            return ExtractionResult(
                success=True,
                data=extracted_data,
                field_evidences=evidences,
                page_title=inspection.get("page_title"),
                target_url=target_url,
                latency_ms=latency_ms,
                evidence_ref=inspection.get("evidence_ref"),
            )

        except Exception as e:
            latency_ms = int((time.monotonic() - start_time) * 1000)
            logger.error("Error during extraction on page: %s", e)
            return ExtractionResult(
                success=False,
                data=None,
                field_evidences=[],
                page_title=None,
                target_url=target_url,
                latency_ms=latency_ms,
                error_code=FailureCode.BROWSER_RESOURCE_ERROR,
                error_message=f"Browser extraction error: {e}",
            )

    async def extract(
        self,
        endpoint_id: str,
        target_url: str,
        schema_definition: dict[str, str],
        selector_map: dict[str, str],
    ) -> ExtractionResult:
        """
        Launches isolated browser session, navigates safely, and extracts data.
        """
        start_time = time.monotonic()
        try:
            from morphapi.browser.source_policy import source_policy_service
            await source_policy_service.enforce_policy(target_url)
            async with self.manager.new_page_session(target_url=target_url) as page:
                await self.manager.navigate_safely(page, target_url)
                return await self.extract_from_page(
                    page=page,
                    endpoint_id=endpoint_id,
                    target_url=target_url,
                    schema_definition=schema_definition,
                    selector_map=selector_map,
                )
        except MorphApiError as me:
            latency_ms = int((time.monotonic() - start_time) * 1000)
            return ExtractionResult(
                success=False,
                data=None,
                field_evidences=[],
                page_title=None,
                target_url=target_url,
                latency_ms=latency_ms,
                error_code=me.code,
                error_message=me.message,
            )
        except Exception as ex:
            latency_ms = int((time.monotonic() - start_time) * 1000)
            return ExtractionResult(
                success=False,
                data=None,
                field_evidences=[],
                page_title=None,
                target_url=target_url,
                latency_ms=latency_ms,
                error_code=FailureCode.BROWSER_EXECUTION_ERROR if hasattr(FailureCode, "BROWSER_EXECUTION_ERROR") else FailureCode.BROWSER_RESOURCE_ERROR,
                error_message=f"Unexpected extraction failure: {ex}",
            )
