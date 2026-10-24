"""
Unit Tests for MorphAPI V2 Semantic Validator Gate
"""

import pytest
from morphapi_v2.engine.semantic_validator import semantic_validator_v2


def test_validator_rejects_navigation_links():
    # Exactly what happened in the user's reported bug
    garbage_data = [
        {"title": "https://www.ycombinator.com/", "link": "https://www.ycombinator.com/"},
        {"title": "https://www.ycombinator.com/about", "link": "https://www.ycombinator.com/about"},
        {"title": "https://www.ycombinator.com/about", "link": "https://www.ycombinator.com/about"},
        {"title": "https://www.ycombinator.com/apply", "link": "https://www.ycombinator.com/apply"},
        {"title": "https://www.ycombinator.com/interviews", "link": "https://www.ycombinator.com/interviews"},
    ]
    schema = {"title": "str", "link": "str"}

    is_valid, issues = semantic_validator_v2.validate_dataset(garbage_data, schema)
    assert not is_valid
    assert any("navigation" in issue.lower() for issue in issues)


def test_validator_rejects_low_diversity_boilerplate():
    boilerplate_data = [
        {"name": "Sign In to View", "link": "https://example.com/item/1"},
        {"name": "Sign In to View", "link": "https://example.com/item/2"},
        {"name": "Sign In to View", "link": "https://example.com/item/3"},
        {"name": "Sign In to View", "link": "https://example.com/item/4"},
    ]
    schema = {"name": "str", "link": "str"}

    is_valid, issues = semantic_validator_v2.validate_dataset(boilerplate_data, schema)
    assert not is_valid
    assert any("diversity" in issue.lower() for issue in issues)


def test_validator_accepts_clean_dataset():
    good_data = [
        {"company_name": "Stripe", "description": "Financial infrastructure", "link": "https://ycombinator.com/companies/stripe"},
        {"company_name": "Airbnb", "description": "Vacation rentals", "link": "https://ycombinator.com/companies/airbnb"},
        {"company_name": "Coinbase", "description": "Crypto platform", "link": "https://ycombinator.com/companies/coinbase"},
        {"company_name": "DoorDash", "description": "Food delivery", "link": "https://ycombinator.com/companies/doordash"},
    ]
    schema = {"company_name": "str", "description": "str", "link": "str"}

    is_valid, issues = semantic_validator_v2.validate_dataset(good_data, schema)
    assert is_valid
    assert len(issues) == 0
