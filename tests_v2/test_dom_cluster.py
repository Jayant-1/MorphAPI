"""
Unit Tests for MorphAPI V2 DOM Cluster & Semantic Container Analyzer
"""

import pytest
from morphapi_v2.browser.dom_cluster import dom_cluster_analyzer

HTML_MOCK_DIRECTORY = """
<!DOCTYPE html>
<html>
<head><title>Startups Directory</title></head>
<body>
    <header>
        <nav>
            <a href="/">Home</a>
            <a href="/about">About</a>
            <a href="/apply">Apply</a>
            <a href="/interviews">Interviews</a>
        </nav>
    </header>
    <div class="sidebar">
        <a href="/filter">Filter</a>
    </div>
    <main id="content">
        <h1>Company Directory</h1>
        <div class="directory-list">
            <a href="/companies/acme" class="company-card">
                <span class="coName">Acme Corp</span>
                <p class="desc">Making anvils for coyotes.</p>
            </a>
            <a href="/companies/globex" class="company-card">
                <span class="coName">Globex Global</span>
                <p class="desc">High tech international conglomerate.</p>
            </a>
            <a href="/companies/initech" class="company-card">
                <span class="coName">Initech Software</span>
                <p class="desc">Enterprise accounting software.</p>
            </a>
        </div>
    </main>
    <footer>
        <a href="/privacy">Privacy</a>
        <a href="/terms">Terms</a>
    </footer>
</body>
</html>
"""


def test_dom_cluster_ignores_navigation_and_finds_cards():
    schema = {"company_name": "str", "description": "str", "link": "str"}
    plan = dom_cluster_analyzer.analyze_dom(HTML_MOCK_DIRECTORY, schema)

    assert plan is not None
    assert plan.strategy == "hierarchical_dom"
    # Container must match the company cards, NOT nav or footer!
    assert "company-card" in plan.container_selector or "a[href*='/companies/']" in plan.container_selector

    # Field rules
    assert "link" in plan.field_rules
    assert plan.field_rules["link"].attribute == "href"

    assert "company_name" in plan.field_rules
    assert "coName" in plan.field_rules["company_name"].selector or "span" in plan.field_rules["company_name"].selector

    assert "description" in plan.field_rules
    assert "desc" in plan.field_rules["description"].selector or "p" in plan.field_rules["description"].selector


HTML_MOCK_TABLE = """
<table>
    <thead>
        <tr><th>Ticker</th><th>Price</th><th>Exchange</th></tr>
    </thead>
    <tbody>
        <tr><td>AAPL</td><td>180.50</td><td>NASDAQ</td></tr>
        <tr><td>MSFT</td><td>410.20</td><td>NASDAQ</td></tr>
        <tr><td>GOOG</td><td>175.10</td><td>NASDAQ</td></tr>
    </tbody>
</table>
"""


def test_dom_cluster_table_layout():
    schema = {"ticker": "str", "price": "str", "exchange": "str"}
    plan = dom_cluster_analyzer.analyze_dom(HTML_MOCK_TABLE, schema)

    assert plan is not None
    assert "tr" in plan.container_selector
    assert "td:nth-child(1)" in plan.field_rules["ticker"].selector
    assert "td:nth-child(2)" in plan.field_rules["price"].selector
    assert "td:nth-child(3)" in plan.field_rules["exchange"].selector
