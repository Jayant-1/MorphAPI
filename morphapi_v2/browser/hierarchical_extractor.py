"""
Hierarchical Browser Extractor for MorphAPI V2
Iterates over repeating container elements and extracts relative child fields,
ensuring perfect alignment across records without flat list zipping errors.
"""

import logging
import time
from urllib.parse import urljoin
from typing import Any
from playwright.async_api import Page

from morphapi_v2.schemas.models import ContainerExtractionPlan, ExtractionResult
from morphapi_v2.engine.type_coercer import type_coercer

logger = logging.getLogger("morphapi_v2.extractor")


class HierarchicalExtractor:
    def __init__(self):
        pass

    async def extract_with_plan(
        self,
        page: Page,
        plan: ContainerExtractionPlan,
        target_schema: dict[str, str],
        max_records: int = 50,
        runtime_params: dict[str, Any] | None = None,
    ) -> ExtractionResult:
        start_ts = time.monotonic()
        base_url = page.url

        # Field specs for type coercion
        field_specs = target_schema
        if plan.contract and plan.contract.fields:
            field_specs = {f.name: f.target_type for f in plan.contract.fields}

        # Custom Playwright browser script execution
        if plan.strategy == "custom_js" and plan.custom_js_extractor:
            try:
                logger.info("[HierarchicalExtractor] Executing custom Playwright script in browser sandbox with params: %s", runtime_params)
                raw_data = await page.evaluate(plan.custom_js_extractor, runtime_params or {})
                if not isinstance(raw_data, list) and not isinstance(raw_data, dict):
                    raw_data = []

                if isinstance(raw_data, dict):
                    coerced = type_coercer.coerce_record(raw_data, field_specs, base_url=base_url)
                    data_res = [coerced]
                else:
                    data_res = type_coercer.coerce_dataset(raw_data[:max_records], field_specs, base_url=base_url)

                latency = int((time.monotonic() - start_ts) * 1000)
                return ExtractionResult(
                    success=True,
                    data=data_res,
                    count=len(data_res),
                    latency_ms=latency,
                    strategy_used="custom_js",
                )
            except Exception as e:
                latency = int((time.monotonic() - start_ts) * 1000)
                logger.error("[HierarchicalExtractor] Custom script execution failure: %s", e)
                return ExtractionResult(
                    success=False,
                    data=None,
                    count=0,
                    latency_ms=latency,
                    error_message=f"Custom browser script error: {e}",
                )

        if not plan.container_selector:
            return ExtractionResult(
                success=False,
                data=[],
                count=0,
                latency_ms=0,
                error_message="No container selector specified in extraction plan",
            )

        try:
            container_locator = page.locator(plan.container_selector)
            container_count = await container_locator.count()
            logger.info("[HierarchicalExtractor] Container selector '%s' matched %d items", plan.container_selector, container_count)

            if container_count == 0:
                return ExtractionResult(
                    success=False,
                    data=[],
                    count=0,
                    latency_ms=int((time.monotonic() - start_ts) * 1000),
                    error_message=f"Container selector '{plan.container_selector}' matched 0 elements",
                )

            dataset: list[dict[str, Any]] = []
            records_to_inspect = min(container_count, max_records)

            for idx in range(records_to_inspect):
                card = container_locator.nth(idx)
                record: dict[str, Any] = {}

                for field_name, rule in plan.field_rules.items():
                    val = await self._extract_field_value(card, rule, base_url)
                    record[field_name] = val

                dataset.append(record)

            coerced_dataset = type_coercer.coerce_dataset(dataset, field_specs, base_url=base_url)

            latency = int((time.monotonic() - start_ts) * 1000)
            return ExtractionResult(
                success=True,
                data=coerced_dataset,
                count=len(coerced_dataset),
                latency_ms=latency,
                strategy_used="hierarchical_dom",
            )

        except Exception as e:
            latency = int((time.monotonic() - start_ts) * 1000)
            logger.error("[HierarchicalExtractor] Extraction failure: %s", e)
            return ExtractionResult(
                success=False,
                data=None,
                count=0,
                latency_ms=latency,
                error_message=f"Extraction error: {e}",
            )

    async def _extract_field_value(self, card_locator, rule, base_url: str) -> str | None:
        """Extracts field value from inside card_locator according to rule."""
        selectors_to_try = [rule.selector] + [fb for fb in rule.fallback_selectors if fb != rule.selector]

        for sel in selectors_to_try:
            try:
                if sel == "." or not sel:
                    target = card_locator
                else:
                    target = card_locator.locator(sel).first

                if await target.count() == 0:
                    continue

                if rule.attribute == "href":
                    raw_href = await target.get_attribute("href")
                    if raw_href:
                        full_url = urljoin(base_url, raw_href.strip())
                        return full_url
                elif rule.attribute == "src":
                    raw_src = await target.get_attribute("src")
                    if raw_src:
                        return urljoin(base_url, raw_src.strip())
                elif rule.attribute in ("value", "title", "alt"):
                    val = await target.get_attribute(rule.attribute)
                    if val and val.strip():
                        return val.strip()
                else:
                    text = await target.inner_text()
                    if text and text.strip():
                        cleaned = " ".join(text.split())
                        return cleaned
            except Exception:
                continue

        # If rule was link and nothing matched, try any anchor in the card
        if any(k in rule.attribute for k in ("href", "link", "url")):
            try:
                a_count = await card_locator.locator("a").count()
                if a_count > 0:
                    raw_href = await card_locator.locator("a").first.get_attribute("href")
                    if raw_href:
                        return urljoin(base_url, raw_href.strip())
            except Exception:
                pass

        return None


hierarchical_extractor = HierarchicalExtractor()
