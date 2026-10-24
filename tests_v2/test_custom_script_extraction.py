"""
Unit and Integration Tests for Custom Playwright Script Browser Extraction in MorphAPI V2
Tests multi-row sibling navigation (Hacker News layout), error handling, and semantic validation.
"""

import pytest
from playwright.async_api import async_playwright

from morphapi_v2.schemas.models import ContainerExtractionPlan
from morphapi_v2.browser.hierarchical_extractor import HierarchicalExtractor
from morphapi_v2.engine.semantic_validator import SemanticValidatorV2
from morphapi_v2.agent.tools import tool_registry_v2


HACKER_NEWS_MOCK_HTML = """
<!DOCTYPE html>
<html>
<head>
    <base href="https://news.ycombinator.com/">
    <title>Hacker News</title>
</head>
<body>
    <table id="hnmain">
        <tr class="athing" id="101">
            <td class="title">
                <span class="titleline">
                    <a href="https://news.ycombinator.com/item?id=101">Show HN: Distributed Memory Cache</a>
                </span>
            </td>
        </tr>
        <tr>
            <td class="subtext">
                <span class="score">342 points</span> by user1 3 hours ago
            </td>
        </tr>
        <tr class="spacer" style="height:5px"></tr>

        <tr class="athing" id="102">
            <td class="title">
                <span class="titleline">
                    <a href="https://example.com/deep-dive">A Deep Dive into Linux Epoll</a>
                </span>
            </td>
        </tr>
        <tr>
            <td class="subtext">
                <span class="score">128 points</span> by user2 5 hours ago
            </td>
        </tr>
        <tr class="spacer" style="height:5px"></tr>

        <tr class="athing" id="103">
            <td class="title">
                <span class="titleline">
                    <a href="https://blog.rust-lang.org/2026/features">Rust Next-Gen Concurrency Primitives</a>
                </span>
            </td>
        </tr>
        <tr>
            <td class="subtext">
                <span class="score">489 points</span> by user3 8 hours ago
            </td>
        </tr>
        <tr class="spacer" style="height:5px"></tr>
    </table>
</body>
</html>
"""

HN_CUSTOM_JS_EXTRACTOR = """
() => {
    const results = [];
    document.querySelectorAll('tr.athing').forEach(tr => {
        const titleEl = tr.querySelector('span.titleline > a');
        const subtr = tr.nextElementSibling;
        const scoreEl = subtr ? subtr.querySelector('.score') : null;
        if (titleEl) {
            results.push({
                story_titles: titleEl.innerText.trim(),
                links: titleEl.href,
                scores: scoreEl ? scoreEl.innerText.trim() : '0 points'
            });
        }
    });
    return results;
}
"""


@pytest.mark.asyncio
async def test_custom_js_extractor_multi_row_sibling_layout():
    """Verify custom script traverses sibling <tr> elements in Chromium sandbox."""
    extractor = HierarchicalExtractor()
    plan = ContainerExtractionPlan(
        strategy="custom_js",
        container_selector="",
        custom_js_extractor=HN_CUSTOM_JS_EXTRACTOR,
        rationale="Traverses sibling <tr> rows to capture score alongside title and link",
    )

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content(HACKER_NEWS_MOCK_HTML)

        res = await extractor.extract_with_plan(
            page=page,
            plan=plan,
            target_schema={"story_titles": "str", "links": "str", "scores": "str"},
            max_records=10,
        )

        await browser.close()

    assert res.success is True
    assert res.strategy_used == "custom_js"
    assert res.count == 3
    assert len(res.data) == 3

    first = res.data[0]
    assert first["story_titles"] == "Show HN: Distributed Memory Cache"
    assert first["links"] == "https://news.ycombinator.com/item?id=101"
    assert first["scores"] == "342 points"

    second = res.data[1]
    assert second["story_titles"] == "A Deep Dive into Linux Epoll"
    assert second["links"] == "https://example.com/deep-dive"
    assert second["scores"] == "128 points"

    third = res.data[2]
    assert third["story_titles"] == "Rust Next-Gen Concurrency Primitives"
    assert third["scores"] == "489 points"


@pytest.mark.asyncio
async def test_custom_script_extraction_passes_semantic_validation():
    """Verify that multi-row extracted data passes 100% semantic validation gate."""
    extractor = HierarchicalExtractor()
    validator = SemanticValidatorV2()

    plan = ContainerExtractionPlan(
        strategy="custom_js",
        container_selector="",
        custom_js_extractor=HN_CUSTOM_JS_EXTRACTOR,
    )

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content(HACKER_NEWS_MOCK_HTML)

        res = await extractor.extract_with_plan(
            page=page,
            plan=plan,
            target_schema={"story_titles": "str", "links": "str", "scores": "str"},
        )
        await browser.close()

    is_valid, issues = validator.validate_dataset(
        dataset=res.data,
        schema_definition={"story_titles": "str", "links": "str", "scores": "str"},
    )

    assert is_valid is True, f"Validation failed with issues: {issues}"
    assert len(issues) == 0


def test_tool_registry_has_custom_browser_script():
    """Verify test_custom_browser_script is exposed in tool definitions and schema."""
    tools = tool_registry_v2.get_tool_definitions()
    tool_map = {t["function"]["name"]: t["function"] for t in tools}

    assert "test_custom_browser_script" in tool_map
    script_tool = tool_map["test_custom_browser_script"]
    assert "js_code" in script_tool["parameters"]["properties"]


@pytest.mark.asyncio
async def test_submit_extraction_plan_with_custom_js():
    """Verify submit_extraction_plan accepts strategy='custom_js' and preserves script."""
    res = await tool_registry_v2.submit_extraction_plan(
        strategy="custom_js",
        custom_js_extractor=HN_CUSTOM_JS_EXTRACTOR,
        rationale="Hacker News multi-row sibling layout requires custom JS extractor",
    )

    assert res["accepted"] is True
    plan = res["plan"]
    assert plan["strategy"] == "custom_js"
    assert plan["custom_js_extractor"] == HN_CUSTOM_JS_EXTRACTOR
    assert "Hacker News multi-row" in plan["rationale"]


@pytest.mark.asyncio
async def test_custom_script_error_resilience():
    """Verify graceful handling when JavaScript throws an error in Chromium sandbox."""
    extractor = HierarchicalExtractor()
    plan = ContainerExtractionPlan(
        strategy="custom_js",
        container_selector="",
        custom_js_extractor="() => { throw new Error('DOM query exception'); }",
    )

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content("<html><body><div>test</div></body></html>")

        res = await extractor.extract_with_plan(
            page=page,
            plan=plan,
            target_schema={"item": "str"},
        )
        await browser.close()

    assert res.success is False
    assert res.count == 0
    assert "Custom browser script error" in res.error_message
