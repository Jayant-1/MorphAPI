"""
Pytest Fixtures for MorphAPI Tests
Spins up a real lightweight HTTP test server to test live Playwright browser extraction.
"""

import asyncio
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import pytest

# Ensure PYTHONPATH includes MorphAPI root
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


HTML_LEGACY_MANDI = """<!DOCTYPE html>
<html>
<head><title>Pune APMC Mandi Rates</title></head>
<body>
  <h1>Market Rates Today</h1>
  <table id="mandi-table">
    <thead>
      <tr><th>Commodity</th><th>Price (INR/Q)</th></tr>
    </thead>
    <tbody>
      <tr><td class="mandi-crop">Wheat</td><td class="rate-val">₹2,450.00</td></tr>
      <tr><td class="mandi-crop">Rice</td><td class="rate-val">₹3,100.50</td></tr>
      <tr><td class="mandi-crop">Onion</td><td class="rate-val">₹1,850.00</td></tr>
    </tbody>
  </table>
</body>
</html>
"""

HTML_MUTATED_MANDI = """<!DOCTYPE html>
<html>
<head><title>Pune APMC Modern Portal</title></head>
<body>
  <header><div class="brand">APMC Digital</div></header>
  <div class="grid-container">
    <div class="crop-card" data-testid="card-1">
      <span class="commodity-title">Wheat</span>
      <span class="market-price">2450.00</span>
    </div>
    <div class="crop-card" data-testid="card-2">
      <span class="commodity-title">Rice</span>
      <span class="market-price">3100.50</span>
    </div>
    <div class="crop-card" data-testid="card-3">
      <span class="commodity-title">Onion</span>
      <span class="market-price">1850.00</span>
    </div>
  </div>
</body>
</html>
"""

HTML_SINGLE_PRODUCT = """<!DOCTYPE html>
<html>
<head><title>Product Detail</title></head>
<body>
  <div class="product-box">
    <h1 id="product-name">Organic Solar Lantern</h1>
    <div class="price-section">
      <span class="curr-price">$49.99</span>
    </div>
    <div class="meta-section">
      <span class="in-stock">Yes</span>
    </div>
  </div>
</body>
</html>
"""


class MockPortalHTTPHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/legacy":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_LEGACY_MANDI.encode("utf-8"))
        elif self.path == "/mutated":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_MUTATED_MANDI.encode("utf-8"))
        elif self.path == "/product":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_SINGLE_PRODUCT.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def log_message(self, format, *args):
        # Suppress logging during tests
        pass


@pytest.fixture(scope="session")
def live_server_url():
    """Starts a real in-process HTTP server for Playwright browser testing."""
    server = HTTPServer(("127.0.0.1", 0), MockPortalHTTPHandler)
    port = server.server_port
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    url = f"http://127.0.0.1:{port}"
    yield url
    server.shutdown()
    server.server_close()
