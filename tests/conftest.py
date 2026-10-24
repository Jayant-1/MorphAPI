"""
MorphAPI Test Fixtures & Configuration
Provides real local HTTP server fixtures serving dynamic HTML,
real Playwright browser instances, and provider test doubles.
"""

import asyncio
import os
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
import pytest
import pytest_asyncio
from playwright.async_api import async_playwright

from morphapi.browser.playwright_manager import PlaywrightManager
from morphapi.browser.url_policy import UrlPolicyService
from morphapi.services.validation_service import ValidationService

# Sample HTML Pages for testing
HTML_SINGLE_PRODUCT = """
<!DOCTYPE html>
<html>
<head><title>Organic Fuji Apples - MorphMarket</title></head>
<body>
    <div id="product-card">
        <h1 class="product-title">Organic Fuji Apples</h1>
        <div class="product-price">$4.99</div>
        <span class="product-stock">In Stock</span>
        <div class="product-date">2026-10-24</div>
    </div>
</body>
</html>
"""

HTML_PRODUCT_BROKEN_SELECTORS = """
<!DOCTYPE html>
<html>
<head><title>Organic Fuji Apples - MorphMarket (Redesigned)</title></head>
<body>
    <main class="storefront">
        <h2 class="item-heading">Organic Fuji Apples</h2>
        <span class="cost-badge">$4.99</span>
        <div class="inventory-status">Available</div>
        <time datetime="2026-10-24" class="restock-date">2026-10-24</time>
    </main>
</body>
</html>
"""

HTML_DYNAMIC_TABLE = """
<!DOCTYPE html>
<html>
<head><title>Live Commodities Exchange</title></head>
<body>
    <table id="commodities-table">
        <thead>
            <tr><th>Commodity</th><th>Price</th><th>Unit</th></tr>
        </thead>
        <tbody id="rows">
            <tr><td class="name">Wheat</td><td class="rate">$220.50</td><td class="unit">ton</td></tr>
            <tr><td class="name">Corn</td><td class="rate">$185.75</td><td class="unit">ton</td></tr>
            <tr><td class="name">Soybeans</td><td class="rate">$410.00</td><td class="unit">ton</td></tr>
        </tbody>
    </table>
</body>
</html>
"""

HTML_REDIRECT_SSRF = """
<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="refresh" content="0; url=http://169.254.169.254/latest/meta-data/">
    <title>Redirecting</title>
</head>
<body>Redirecting to internal resource...</body>
</html>
"""


class TestHttpServerHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()

        path = self.path
        if path == "/product":
            self.wfile.write(HTML_SINGLE_PRODUCT.encode("utf-8"))
        elif path == "/product-redesign":
            self.wfile.write(HTML_PRODUCT_BROKEN_SELECTORS.encode("utf-8"))
        elif path == "/commodities":
            self.wfile.write(HTML_DYNAMIC_TABLE.encode("utf-8"))
        elif path == "/ssrf-redirect":
            self.wfile.write(HTML_REDIRECT_SSRF.encode("utf-8"))
        else:
            self.wfile.write(b"<html><body><h1>Default MorphAPI Test Page</h1></body></html>")

    def log_message(self, format, *args):
        pass  # Suppress console logging during tests


@pytest.fixture(scope="session")
def test_http_server():
    """Starts local fixture HTTP server on localhost."""
    server = HTTPServer(("127.0.0.1", 0), TestHttpServerHandler)
    port = server.server_port
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{port}"
    yield base_url
    server.shutdown()


@pytest_asyncio.fixture
async def playwright_browser():
    """Provides a real headless Playwright browser instance."""
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True, args=["--no-sandbox"])
    yield browser
    await browser.close()
    await pw.stop()


@pytest.fixture
def local_url_policy():
    """URL policy configured to permit local test server URLs."""
    return UrlPolicyService(allow_local=True)


@pytest.fixture
def strict_url_policy():
    """Strict URL policy blocking local and private IP ranges."""
    return UrlPolicyService(allow_local=False)


@pytest.fixture
def validation_service():
    return ValidationService()
