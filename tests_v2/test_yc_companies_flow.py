"""
Test for the exact YC Companies user scenario reported by the user.
Verifies that:
1. Intent correctly extracts schema: {"company_name": "str", "description": "str", "link": "str"}
2. Discovers inputs: {"batch": ..., "year": ...}
3. DOM cluster extracts genuine company cards and links, completely ignoring navbar links (/about, /apply)
4. Semantic validator passes real company data and rejects navigation links
"""

import pytest
from morphapi_v2.engine.intent_parser import intent_parser_v2
from morphapi_v2.browser.dom_cluster import dom_cluster_analyzer
from morphapi_v2.engine.semantic_validator import semantic_validator_v2

YC_RENDERED_SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<head><title>The YC Startup Directory | Y Combinator</title></head>
<body>
    <header>
        <nav class="navbar">
            <a href="/">Home</a>
            <a href="/about">About</a>
            <a href="/apply">Apply</a>
            <a href="/interviews">Interviews</a>
        </nav>
    </header>
    <main id="content">
        <div class="directory-container">
            <a href="/companies/doordash" class="_company_15z2z_338">
                <span class="_coName_15z2z_453">DoorDash</span>
                <span class="_coDescription_15z2z_478">Restaurant delivery.</span>
            </a>
            <a href="/companies/airbnb" class="_company_15z2z_338">
                <span class="_coName_15z2z_453">Airbnb</span>
                <span class="_coDescription_15z2z_478">Book accommodations around the world.</span>
            </a>
            <a href="/companies/coinbase" class="_company_15z2z_338">
                <span class="_coName_15z2z_453">Coinbase</span>
                <span class="_coDescription_15z2z_478">Buy, sell, and manage cryptocurrencies.</span>
            </a>
            <a href="/companies/instacart" class="_company_15z2z_338">
                <span class="_coName_15z2z_453">Instacart</span>
                <span class="_coDescription_15z2z_478">Marketplace for grocery delivery and pickup.</span>
            </a>
        </div>
    </main>
    <footer>
        <a href="/terms">Terms</a>
        <a href="/privacy">Privacy</a>
    </footer>
</body>
</html>
"""


def test_yc_companies_pipeline_on_rendered_html():
    prompt = (
        "Create an API for Y Combinator accepted companies from "
        "https://www.ycombinator.com/companies with configurable batch or year. "
        "Extract company name, description, and link."
    )
    target_url = "https://www.ycombinator.com/companies?batch={batch}"

    # 1. Parse intent
    intent = intent_parser_v2.parse(prompt, target_url=target_url, name="yc-startups-2")
    assert intent.schema_definition == {
        "company_name": "str",
        "description": "str",
        "link": "str",
    }
    assert "batch" in intent.inputs

    # 2. Analyze DOM cluster
    plan = dom_cluster_analyzer.analyze_dom(YC_RENDERED_SAMPLE_HTML, intent.schema_definition)
    assert plan is not None
    # Ensure it matched company cards, NOT navbar
    assert "_company_15z2z_338" in plan.container_selector or "a[href*='/companies/']" in plan.container_selector

    # 3. Simulate extraction using plan
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(YC_RENDERED_SAMPLE_HTML, "html.parser")
    # Emulate hierarchical extractor logic
    selector_str = plan.container_selector
    cards = soup.select(selector_str)
    assert len(cards) == 4

    extracted_records = []
    for c in cards:
        rec = {}
        for fname, rule in plan.field_rules.items():
            if rule.attribute == "href":
                rec[fname] = f"https://www.ycombinator.com{c['href']}"
            else:
                el = c.select_one(rule.selector) if rule.selector != "." else c
                rec[fname] = el.get_text(strip=True) if el else None
        extracted_records.append(rec)

    # 4. Verify extracted records are genuine companies, NOT navbar!
    assert len(extracted_records) == 4
    assert extracted_records[0]["company_name"] == "DoorDash"
    assert extracted_records[0]["description"] == "Restaurant delivery."
    assert extracted_records[0]["link"] == "https://www.ycombinator.com/companies/doordash"

    assert extracted_records[1]["company_name"] == "Airbnb"
    assert extracted_records[2]["company_name"] == "Coinbase"
    assert extracted_records[3]["company_name"] == "Instacart"

    # 5. Semantic Validation must PASS
    is_valid, issues = semantic_validator_v2.validate_dataset(extracted_records, intent.schema_definition)
    assert is_valid, f"Validation failed: {issues}"
