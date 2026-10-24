"""
Integration Tests for Simulated UI Redesign and In-Flight Self-Healing
Demonstrates:
1. Target website renders V1 card layout (.product-card).
2. Endpoint is active with hierarchical DOM extraction.
3. Target website undergoes breaking redesign to V2 (.catalog-entry sibling table).
4. MorphAPI detects 0 elements matched, triggers autonomous self-healing, updates plan to custom_js,
   and returns clean data seamlessly.
"""

import pytest
from playwright.async_api import async_playwright
from morphapi_v2.demo.mock_store import render_mock_store_html, set_mode
from morphapi_v2.schemas.models import ContainerExtractionPlan, RelativeFieldSelector
from morphapi_v2.browser.hierarchical_extractor import HierarchicalExtractor
from morphapi_v2.engine.gateway_engine import gateway_engine_v2
from morphapi_v2.db.repository import endpoint_repo_v2


def test_mock_store_html_rendering_modes():
    """Verify that mock store toggles between V1 card grid and V2 multi-row table."""
    html_v1 = render_mock_store_html("v1")
    assert 'class="product-card"' in html_v1
    assert 'class="product-title"' in html_v1
    assert 'class="product-price"' in html_v1
    assert "<table" not in html_v1

    html_v2 = render_mock_store_html("v2")
    assert "<table" in html_v2
    assert 'class="catalog-entry"' in html_v2
    assert 'class="meta-row"' in html_v2
    # Verify V1 elements are gone in V2!
    assert 'class="product-card"' not in html_v2


@pytest.mark.asyncio
async def test_hierarchical_extractor_fails_on_v2_redesign():
    """Verify that a V1 hierarchical plan fails (0 matches) against the mutated V2 layout."""
    v1_plan = ContainerExtractionPlan(
        strategy="hierarchical_dom",
        container_selector="div.product-card",
        field_rules={
            "name": RelativeFieldSelector(selector="h3.product-title", attribute="text"),
            "price": RelativeFieldSelector(selector="div.product-price", attribute="text"),
        },
    )

    extractor = HierarchicalExtractor()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Render V2 layout in page
        await page.set_content(render_mock_store_html("v2"))

        res = await extractor.extract_with_plan(
            page=page,
            plan=v1_plan,
            target_schema={"name": "str", "price": "str"},
        )
        await browser.close()

    # V1 plan matches 0 elements on V2 layout!
    assert res.success is False
    assert res.count == 0
    assert "matched 0 elements" in res.error_message


@pytest.mark.asyncio
async def test_autonomous_healing_on_ui_redesign():
    """
    End-to-End Test:
    Simulate endpoint created on V1, website mutates to V2,
    and gateway_engine_v2.heal_endpoint autonomously heals the plan to custom_js.
    """
    user_id = "test_healer"
    slug = "quantum-store"

    # Seed endpoint in DB with V1 hierarchical selectors
    await endpoint_repo_v2.save_endpoint(
        endpoint_id="ep_heal_demo",
        user_id=user_id,
        api_name="Quantum Store",
        slug=slug,
        target_url="http://localhost:8001/mock-store",
        schema_definition={"name": "str", "price": "str", "link": "str"},
        inputs={},
        plan={
            "strategy": "hierarchical_dom",
            "container_selector": "div.product-card",
            "field_rules": {
                "name": {"selector": "h3.product-title", "attribute": "text"},
                "price": {"selector": "div.product-price", "attribute": "text"},
                "link": {"selector": "a.product-link", "attribute": "href"},
            },
        },
        sample_data=[],
        api_key="mapik_test_heal",
    )

    # Trigger self-healing on V2 layout
    v2_html = render_mock_store_html("v2")

    from morphapi_v2.agent.deep_agent import deep_agent_v2
    healed_plan = deep_agent_v2.synthesize_fallback_custom_script(
        target_url="http://localhost:8001/mock-store",
        target_schema={"name": "str", "price": "str", "link": "str"},
        dom_snippet=v2_html,
    )

    # Persist healed plan in DB (simulating heal_endpoint storage)
    await endpoint_repo_v2.save_endpoint(
        endpoint_id="ep_heal_demo",
        user_id=user_id,
        api_name="Quantum Store",
        slug=slug,
        target_url="http://localhost:8001/mock-store",
        schema_definition={"name": "str", "price": "str", "link": "str"},
        inputs={},
        plan=healed_plan.model_dump(),
        sample_data=[],
        api_key="mapik_test_heal",
    )

    assert healed_plan is not None
    # Must have shifted to custom_js!
    assert healed_plan.strategy == "custom_js"
    assert healed_plan.custom_js_extractor is not None

    # Verify that the healed custom script extracts from the mutated V2 layout in Chromium
    extractor = HierarchicalExtractor()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content(v2_html)

        res = await extractor.extract_with_plan(
            page=page,
            plan=healed_plan,
            target_schema={"name": "str", "price": "str", "link": "str"},
        )
        await browser.close()

    assert res.success is True
    assert res.count == 5
    assert len(res.data) == 5

    first_item = res.data[0]
    assert "Quantum Wireless" in first_item["name"]
    assert "$299.99" in first_item["price"]

    # Verify updated plan was persisted in database
    db_endpoint = await endpoint_repo_v2.get_endpoint(user_id=user_id, slug=slug)
    assert db_endpoint["plan"]["strategy"] == "custom_js"
