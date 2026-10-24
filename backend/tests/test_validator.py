"""
Tests for deterministic normalizer and schema validation.
"""

import pytest
from backend.app.services.validator import (
    normalize_string,
    normalize_float,
    normalize_int,
    normalize_bool,
    normalize_date,
    validate_and_normalize_record,
    validate_and_normalize_dataset,
)


def test_normalize_string():
    assert normalize_string("   Hello   World  \n\t") == "Hello World"
    assert normalize_string(None) == ""


def test_normalize_float():
    assert normalize_float("$2,450.50") == 2450.50
    assert normalize_float("₹ 1,800.00 / Q") == 1800.0
    assert normalize_float("€ 99.95") == 99.95
    assert normalize_float("-15.4%") == -15.4

    with pytest.raises(ValueError):
        normalize_float("No numbers here")

    with pytest.raises(ValueError):
        normalize_float(None)


def test_normalize_int():
    assert normalize_int("1,234") == 1234
    assert normalize_int("500.00") == 500


def test_normalize_bool():
    assert normalize_bool("true") is True
    assert normalize_bool("Yes") is True
    assert normalize_bool("1") is True
    assert normalize_bool("active") is True
    assert normalize_bool("false") is False
    assert normalize_bool("No") is False
    assert normalize_bool("0") is False

    with pytest.raises(ValueError):
        normalize_bool("maybe")


def test_normalize_date():
    assert normalize_date("2026-10-24") == "2026-10-24"
    assert normalize_date("24/10/2026") == "2026-10-24"
    assert normalize_date("October 24, 2026") == "2026-10-24"

    with pytest.raises(ValueError):
        normalize_date("invalid-date-string")


def test_validate_and_normalize_record_success():
    schema = {"crop": "str", "price": "float", "in_stock": "bool"}
    raw = {"crop": "  Wheat  ", "price": "₹ 2,450.00", "in_stock": "yes"}
    is_valid, norm, errors = validate_and_normalize_record(raw, schema)
    assert is_valid is True
    assert errors == []
    assert norm == {"crop": "Wheat", "price": 2450.0, "in_stock": True}


def test_validate_and_normalize_record_missing_field():
    schema = {"crop": "str", "price": "float"}
    raw = {"crop": "Wheat"}  # missing price
    is_valid, norm, errors = validate_and_normalize_record(raw, schema)
    assert is_valid is False
    assert any("price" in e for e in errors)


def test_validate_and_normalize_record_invalid_type():
    schema = {"price": "float"}
    raw = {"price": "Not a number"}
    is_valid, norm, errors = validate_and_normalize_record(raw, schema)
    assert is_valid is False
    assert any("failed validation" in e for e in errors)


def test_validate_and_normalize_dataset_list():
    schema = {"crop": "str", "price": "float"}
    raw_list = [
        {"crop": "Wheat", "price": "2,450.00"},
        {"crop": "Rice", "price": "3,100.50"},
    ]
    is_valid, norm_list, errors = validate_and_normalize_dataset(raw_list, schema)
    assert is_valid is True
    assert len(norm_list) == 2
    assert norm_list[0] == {"crop": "Wheat", "price": 2450.0}
    assert norm_list[1] == {"crop": "Rice", "price": 3100.5}


def test_validate_and_normalize_dataset_empty_list():
    schema = {"crop": "str"}
    is_valid, norm, errors = validate_and_normalize_dataset([], schema)
    assert is_valid is False
    assert "empty list" in errors[0]
