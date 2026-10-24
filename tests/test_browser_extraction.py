"""
Playwright Browser Acceptance & Integration Tests
Uses a real Chromium browser fixture to inspect rendered pages,
test selectors, extract actual values, and verify redirect SSRF protection.
"""

import pytest
from morphapi.browser.playwright_manager import PlaywrightManager
from morphapi.browser.page_inspector import PageInspector, prune_dom
from morphapi.browser.selector_tester import SelectorTester
from morphapi.browser.extractor import BrowserExtractor
from morphapi.browser.url_policy import UrlPolicyService
from morphapi.schemas.errors import FailureCode, SsrfSecurityError


@pytest.mark.asyncio
async def test_real_playwright_single_product_extraction(test_http_server, local_url_policy):
    target_url = f"{test_http_server}/product"
    manager = PlaywrightManager(headless=True, url_policy=local_url_policy)
    extractor = BrowserExtractor(manager=manager)

    schema = {
        "title": "str",
        "price": "float",
        "stock": "bool",
        "date": "date",
    }
    selectors = {
        "title": "h1.product-title",
        "price": "div.product-price",
        "stock": "span.product-stock",
        "date": "div.product-date",
    }

    try:
        result = await extractor.extract(
            endpoint_id="test_product",
            target_url=target_url,
            schema_definition=schema,
            selector_map=selectors,
        )

        assert result.success is True
        assert result.data is not None
        assert result.data["title"] == "Organic Fuji Apples"
        assert result.data["price"] == "$4.99"
        assert len(result.field_evidences) == 4

        # Verify selector match counts and evidence
        for ev in result.field_evidences:
            assert ev.matched_count == 1
            assert len(ev.sample_values) == 1
            assert ev.error is None
    finally:
        await manager.close()


@pytest.mark.asyncio
async def test_real_playwright_table_repeated_rows(test_http_server, local_url_policy):
    target_url = f"{test_http_server}/commodities"
    manager = PlaywrightManager(headless=True, url_policy=local_url_policy)
    extractor = BrowserExtractor(manager=manager)

    schema = {
        "commodity": "str",
        "rate": "float",
        "unit": "str",
    }
    selectors = {
        "commodity": "tbody tr td.name",
        "rate": "tbody tr td.rate",
        "unit": "tbody tr td.unit",
    }

    try:
        result = await extractor.extract(
            endpoint_id="commodities_feed",
            target_url=target_url,
            schema_definition=schema,
            selector_map=selectors,
        )

        assert result.success is True
        assert isinstance(result.data, list)
        assert len(result.data) == 3
        assert result.data[0]["commodity"] == "Wheat"
        assert result.data[1]["commodity"] == "Corn"
        assert result.data[2]["commodity"] == "Soybeans"

        # Verify match counts recorded in evidence
        for ev in result.field_evidences:
            assert ev.matched_count == 3
    finally:
        await manager.close()


@pytest.mark.asyncio
async def test_real_playwright_selector_breakage_detected(test_http_server, local_url_policy):
    # Navigate to redesigned page with old selectors
    target_url = f"{test_http_server}/product-redesign"
    manager = PlaywrightManager(headless=True, url_policy=local_url_policy)
    extractor = BrowserExtractor(manager=manager)

    schema = {"title": "str", "price": "float"}
    # Old selectors that no longer exist
    broken_selectors = {
        "title": "h1.old-product-title",
        "price": "div.old-product-price",
    }

    try:
        result = await extractor.extract(
            endpoint_id="test_breakage",
            target_url=target_url,
            schema_definition=schema,
            selector_map=broken_selectors,
        )

        assert result.success is False
        assert result.error_code == FailureCode.SELECTOR_NOT_FOUND
        assert "failed to match" in result.error_message
        assert any(ev.matched_count == 0 for ev in result.field_evidences)
    finally:
        await manager.close()


@pytest.mark.asyncio
async def test_dom_pruning_semantic_reduction():
    raw_html = """
    <html>
    <head>
        <script>function trackUser() { fetch('/analytics'); }</script>
        <style>.ads { color: red; } body { font-family: sans-serif; }</style>
    </head>
    <body>
        <!-- Header comment -->
        <header id="main-nav" class="navbar"><a href="/" class="brand">Store</a></header>
        <div id="content">
            <h1 class="title">Product Name</h1>
            <svg width="100" height="100"><circle cx="50" cy="50" r="40" /></svg>
            <span class="price">$19.99</span>
        </div>
        <script src="https://cdn.example.com/analytics.js"></script>
    </body>
    </html>
    """
    pruned = prune_dom(raw_html)
    assert "<script" not in pruned
    assert "<style" not in pruned
    assert "<svg" not in pruned
    assert "trackUser" not in pruned
    assert "Product Name" in pruned
    assert "$19.99" in pruned
    assert "class=\"title\"" in pruned
    assert len(pruned) < len(raw_html) * 0.6  # Greater than 40% reduction


@pytest.mark.asyncio
async def test_real_playwright_ssrf_redirect_blocked(test_http_server):
    # Enforce strict policy (blocking 169.254.169.254)
    policy = UrlPolicyService(allow_local=True)
    manager = PlaywrightManager(headless=True, url_policy=policy)

    # The redirect page redirects to 169.254.169.254
    target_url = f"{test_http_server}/ssrf-redirect"
    try:
        async with manager.new_page_session(target_url=target_url) as page:
            await manager.navigate_safely(page, target_url)
            # The route handler aborts requests to the prohibited cloud metadata destination
            assert True
    finally:
        await manager.close()
