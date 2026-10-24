"""
Real Playwright Extraction Tests.
Executes actual headless Chromium browser sessions against the live test server fixture
and an accessible real web target.
"""

import pytest
from backend.app.services.extraction import PlaywrightExtractionService


@pytest.mark.asyncio
async def test_real_playwright_table_extraction(live_server_url):
    """
    Tests actual Playwright execution against multi-row table fixture.
    """
    service = PlaywrightExtractionService(allow_local=True)
    target_url = f"{live_server_url}/legacy"
    schema = {"crop": "str", "price": "float"}
    selectors = {"crop": ".mandi-crop", "price": ".rate-val"}

    result = await service.extract(
        target_url=target_url,
        schema_definition=schema,
        selectors=selectors,
    )

    await service.close()

    assert result.success is True
    assert result.is_schema_valid is True
    assert isinstance(result.data, list)
    assert len(result.data) == 3

    # Check extracted values and deterministic normalization
    assert result.data[0]["crop"] == "Wheat"
    assert result.data[0]["price"] == 2450.0
    assert result.data[1]["crop"] == "Rice"
    assert result.data[1]["price"] == 3100.5
    assert result.data[2]["crop"] == "Onion"
    assert result.data[2]["price"] == 1850.0

    # Verify diagnostics
    assert result.diagnostics.page_title == "Pune APMC Mandi Rates"
    assert len(result.diagnostics.field_diagnostics) == 2
    assert result.diagnostics.field_diagnostics[0].matched_count == 3


@pytest.mark.asyncio
async def test_real_playwright_single_product_extraction(live_server_url):
    """
    Tests actual Playwright execution against single object page fixture.
    """
    service = PlaywrightExtractionService(allow_local=True)
    target_url = f"{live_server_url}/product"
    schema = {"product": "str", "price": "float", "in_stock": "bool"}
    selectors = {"product": "#product-name", "price": ".curr-price", "in_stock": ".in-stock"}

    result = await service.extract(
        target_url=target_url,
        schema_definition=schema,
        selectors=selectors,
    )

    await service.close()

    assert result.success is True
    assert result.is_schema_valid is True
    assert isinstance(result.data, dict)
    assert result.data["product"] == "Organic Solar Lantern"
    assert result.data["price"] == 49.99
    assert result.data["in_stock"] is True


@pytest.mark.asyncio
async def test_real_playwright_missing_selector(live_server_url):
    """
    Tests that a non-existent selector fails with typed diagnostics and DOES NOT fabricate data.
    """
    service = PlaywrightExtractionService(allow_local=True)
    target_url = f"{live_server_url}/legacy"
    schema = {"crop": "str", "nonexistent_field": "str"}
    selectors = {"crop": ".mandi-crop", "nonexistent_field": ".not-on-page"}

    result = await service.extract(
        target_url=target_url,
        schema_definition=schema,
        selectors=selectors,
    )

    await service.close()

    assert result.success is False
    assert result.data is None
    assert result.error_code == "SELECTOR_FAILED"
    # Verify missing selector diagnostic
    diag = next(d for d in result.diagnostics.field_diagnostics if d.field_name == "nonexistent_field")
    assert diag.matched_count == 0


@pytest.mark.asyncio
async def test_real_playwright_ambiguous_element_counts(live_server_url):
    """
    Tests that mismatched element counts across fields fail with an ambiguity error.
    """
    service = PlaywrightExtractionService(allow_local=True)
    target_url = f"{live_server_url}/legacy"
    # h1 matches 1 element, .mandi-crop matches 3 elements
    schema = {"title": "str", "crop": "str"}
    selectors = {"title": "h1", "crop": ".mandi-crop"}

    result = await service.extract(
        target_url=target_url,
        schema_definition=schema,
        selectors=selectors,
    )

    await service.close()

    assert result.success is False
    assert "Ambiguous element counts" in (result.error_message or "")


@pytest.mark.asyncio
async def test_real_playwright_schema_validation_failure(live_server_url):
    """
    Tests that elements matching but failing type conversion trigger schema validation failure.
    """
    service = PlaywrightExtractionService(allow_local=True)
    target_url = f"{live_server_url}/legacy"
    # Requesting price as date should fail
    schema = {"crop": "str", "price": "date"}
    selectors = {"crop": ".mandi-crop", "price": ".rate-val"}

    result = await service.extract(
        target_url=target_url,
        schema_definition=schema,
        selectors=selectors,
    )

    await service.close()

    assert result.success is False
    assert result.error_code == "SCHEMA_VALIDATION_FAILED"
    assert len(result.validation_errors) > 0


@pytest.mark.asyncio
async def test_real_playwright_navigation_failure():
    """
    Tests that invalid domain or connection failure triggers controlled error.
    """
    service = PlaywrightExtractionService(timeout_ms=3000, allow_local=False)
    # Non-routable external URL
    target_url = "http://invalid-non-existent-morphapi-domain.example"
    schema = {"crop": "str"}
    selectors = {"crop": ".title"}

    result = await service.extract(
        target_url=target_url,
        schema_definition=schema,
        selectors=selectors,
    )

    await service.close()

    assert result.success is False
    assert result.error_code in ("TIMEOUT", "BROWSER_ERROR", "SSRF_PROHIBITED")


@pytest.mark.asyncio
async def test_real_playwright_live_public_website():
    """
    End-to-end scenario against an accessible public website (example.com).
    Uses actual headless Chromium extraction.
    """
    service = PlaywrightExtractionService(timeout_ms=10000, allow_local=False)
    target_url = "http://example.com"
    schema = {"title": "str", "paragraph": "str"}
    selectors = {"title": "title", "paragraph": "p:first-of-type"}

    result = await service.extract(
        target_url=target_url,
        schema_definition=schema,
        selectors=selectors,
    )

    await service.close()

    assert result.success is True
    assert result.is_schema_valid is True
    assert isinstance(result.data, dict)
    assert "Example Domain" in result.data["title"]
    assert len(result.data["paragraph"]) > 10
