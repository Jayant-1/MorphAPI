"""
Unit Tests for Deterministic Validation Service (Pydantic v2)
"""

import pytest
from morphapi.services.validation_service import ValidationService


def test_normalize_string(validation_service):
    val, err = validation_service.normalize_field_value("  Organic Apples  ", "str")
    assert err is None
    assert val == "Organic Apples"

    val, err = validation_service.normalize_field_value("   ", "str")
    assert err is not None
    assert val is None


def test_normalize_float(validation_service):
    # Currency symbols and commas
    val, err = validation_service.normalize_field_value(" $1,299.99 ", "float")
    assert err is None
    assert val == 1299.99

    val, err = validation_service.normalize_field_value("€42.50", "float")
    assert err is None
    assert val == 42.50

    val, err = validation_service.normalize_field_value("not-a-number", "float")
    assert err is not None


def test_normalize_int(validation_service):
    val, err = validation_service.normalize_field_value(" 450 ", "int")
    assert err is None
    assert val == 450

    val, err = validation_service.normalize_field_value("1,200", "int")
    assert err is None
    assert val == 1200

    val, err = validation_service.normalize_field_value("invalid", "int")
    assert err is not None


def test_normalize_bool(validation_service):
    true_cases = ["In Stock", "true", "True", "YES", "1", "available"]
    for c in true_cases:
        val, err = validation_service.normalize_field_value(c, "bool")
        assert err is None
        assert val is True

    false_cases = ["Out of Stock", "false", "0", "no", "unavailable"]
    for c in false_cases:
        val, err = validation_service.normalize_field_value(c, "bool")
        assert err is None
        assert val is False

    val, err = validation_service.normalize_field_value("maybe", "bool")
    assert err is not None


def test_normalize_date(validation_service):
    val, err = validation_service.normalize_field_value("2026-10-24", "date")
    assert err is None
    assert val == "2026-10-24"

    val, err = validation_service.normalize_field_value("October 24, 2026", "date")
    assert err is None
    assert val == "2026-10-24"


def test_validate_single_record_success(validation_service):
    schema = {
        "title": "str",
        "price": "float",
        "in_stock": "bool",
        "date": "date",
    }
    extracted = {
        "title": "Organic Fuji Apples",
        "price": "$4.99",
        "in_stock": "In Stock",
        "date": "2026-10-24",
    }
    result = validation_service.validate_extraction(extracted, schema)
    assert result.is_valid is True
    assert result.errors == []
    assert result.normalized_data["price"] == 4.99
    assert result.normalized_data["in_stock"] is True


def test_validate_single_record_missing_field(validation_service):
    schema = {"title": "str", "price": "float", "missing_field": "str"}
    extracted = {"title": "Organic Fuji Apples", "price": "$4.99"}
    result = validation_service.validate_extraction(extracted, schema)
    assert result.is_valid is False
    assert any("missing_field" in err for err in result.errors)


def test_validate_repeated_list_dataset(validation_service):
    schema = {"commodity": "str", "rate": "float", "unit": "str"}
    extracted = [
        {"commodity": "Wheat", "rate": "$220.50", "unit": "ton"},
        {"commodity": "Corn", "rate": "$185.75", "unit": "ton"},
        {"commodity": "Soybeans", "rate": "$410.00", "unit": "ton"},
    ]
    result = validation_service.validate_extraction(extracted, schema)
    assert result.is_valid is True
    assert len(result.normalized_data) == 3
    assert result.normalized_data[0]["rate"] == 220.50
