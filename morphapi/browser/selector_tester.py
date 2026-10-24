"""
MorphAPI Selector Tester
Executes candidate CSS and XPath selectors against live rendered Playwright pages,
recording actual match counts, sample values, visibility, and element diagnostics.
"""

import logging
from typing import Any
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from morphapi.browser.url_policy import validate_selector_safety
from morphapi.schemas.contracts import FieldEvidence

logger = logging.getLogger("morphapi.selector_tester")


class SelectorTester:
    """
    Tests proposed selectors on a real rendered page and collects field evidence.
    """

    def __init__(self, element_timeout_ms: int = 4000):
        self.element_timeout_ms = element_timeout_ms

    async def test_selector(
        self,
        page: Page,
        field_name: str,
        selector: str,
        max_samples: int = 5,
    ) -> FieldEvidence:
        """
        Executes a selector against the live page, extracting match counts and sample values.
        """
        is_safe, error_msg = validate_selector_safety(selector)
        if not is_safe:
            return FieldEvidence(
                field_name=field_name,
                selector=selector,
                matched_count=0,
                sample_values=[],
                error=f"Unsafe selector: {error_msg}",
            )

        try:
            locator = page.locator(selector)
            count = await locator.count()

            if count == 0:
                return FieldEvidence(
                    field_name=field_name,
                    selector=selector,
                    matched_count=0,
                    sample_values=[],
                    error="Selector matched 0 elements",
                )

            samples: list[Any] = []
            tag_name: str | None = None
            is_visible: bool = True

            # Sample first N elements
            inspect_count = min(count, max_samples)
            for i in range(inspect_count):
                elem = locator.nth(i)
                try:
                    # Extract tag name
                    curr_tag = await elem.evaluate("el => el.tagName.toLowerCase()")
                    if i == 0:
                        is_visible = await elem.is_visible()
                        tag_name = curr_tag

                    # If field expects a URL or element is an anchor/source, extract fully qualified link
                    is_link_field = any(k in field_name.lower() for k in ("link", "url", "href", "doc", "file", "download", "pdf")) or curr_tag == "a" or selector.strip().endswith("a")

                    if is_link_field and curr_tag == "a":
                        href = await elem.evaluate("el => el.href || el.getAttribute('href') || ''")
                        text = href.strip() if href else ""
                        if not text:
                            raw_text = await elem.inner_text()
                            text = raw_text.strip() if raw_text else ""
                    else:
                        raw_text = await elem.inner_text()
                        text = raw_text.strip() if raw_text else ""
                        if not text:
                            # Fallback to attribute checks (value, href, src)
                            text = (
                                await elem.get_attribute("value")
                                or await elem.get_attribute("href")
                                or await elem.get_attribute("src")
                                or ""
                            ).strip()

                    samples.append(text)
                except Exception as ex:
                    logger.debug("Error inspecting element %d for selector '%s': %s", i, selector, ex)
                    samples.append("")

            return FieldEvidence(
                field_name=field_name,
                selector=selector,
                matched_count=count,
                sample_values=samples,
                tag_name=tag_name,
                is_visible=is_visible,
                error=None,
            )

        except PlaywrightTimeoutError:
            return FieldEvidence(
                field_name=field_name,
                selector=selector,
                matched_count=0,
                sample_values=[],
                error=f"Timeout ({self.element_timeout_ms}ms) waiting for selector",
            )
        except Exception as e:
            return FieldEvidence(
                field_name=field_name,
                selector=selector,
                matched_count=0,
                sample_values=[],
                error=f"Selector evaluation error: {e}",
            )

    async def test_all_selectors(
        self,
        page: Page,
        selector_map: dict[str, str],
        max_samples: int = 5,
    ) -> list[FieldEvidence]:
        """
        Tests every field selector in selector_map and collects field evidence list.
        """
        results: list[FieldEvidence] = []
        for field_name, selector in selector_map.items():
            evidence = await self.test_selector(page, field_name, selector, max_samples=max_samples)
            results.append(evidence)
        return results
