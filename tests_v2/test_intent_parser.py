"""
Unit Tests for MorphAPI V2 Intent Parser
"""

import pytest
from morphapi_v2.engine.intent_parser import intent_parser_v2


def test_intent_parser_yc_companies_example():
    prompt = (
        "Create an API for Y Combinator accepted companies from "
        "https://www.ycombinator.com/companies with configurable batch or year. "
        "Extract company name, description, and link."
    )
    target_url = "https://www.ycombinator.com/companies?batch={batch}"
    name = "yc-startups-2"

    intent = intent_parser_v2.parse(prompt=prompt, target_url=target_url, name=name)

    # 1. Verify Name and Slug
    assert intent.slug == "yc-startups-2"
    assert intent.name == "yc-startups-2"
    assert intent.entity_name == "company"

    # 2. Verify Output Schema (Must match user's explicit request!)
    assert "company_name" in intent.schema_definition
    assert "description" in intent.schema_definition
    assert "link" in intent.schema_definition
    assert intent.schema_definition["company_name"] == "str"
    assert intent.schema_definition["description"] == "str"
    assert intent.schema_definition["link"] == "str"

    # 3. Verify Parameterized Inputs
    assert "batch" in intent.inputs
    assert "year" in intent.inputs

    # 4. Verify Inspection URL (Placeholder stripped for live testing)
    assert "{" not in intent.sample_inspection_url
    assert "https://www.ycombinator.com/companies" in intent.sample_inspection_url


def test_intent_parser_ecommerce_example():
    prompt = "Scrape products from https://store.example.com/items?page={page}. Extract title, price, and image."
    intent = intent_parser_v2.parse(prompt=prompt)

    assert "title" in intent.schema_definition
    assert "price" in intent.schema_definition
    assert "image" in intent.schema_definition
    assert intent.schema_definition["price"] == "float"
    assert "page" in intent.inputs
