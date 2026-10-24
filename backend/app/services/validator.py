"""
MorphAPI Deterministic Normalization and Schema Validation Service
Strictly validates extracted raw element text or attributes against customer-defined schema.
Never silently fabricates values for missing fields.
"""

import re
from datetime import datetime
from typing import Any


class SchemaValidationError(Exception):
    """Raised when extracted values cannot be validated or coerced to the target schema."""
    pass


def normalize_string(raw: Any) -> str:
    if raw is None:
        return ""
    text = str(raw).strip()
    # Normalize excessive internal whitespace
    text = re.sub(r"[\r\n\t]+", " ", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text


def normalize_float(raw: Any) -> float:
    if raw is None:
        raise ValueError("Cannot convert None to float")
    text = normalize_string(raw)
    # Remove currency symbols, commas, percent signs
    cleaned = re.sub(r"[\$€₹£¥,\s%]", "", text)
    match = re.search(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", cleaned)
    if not match:
        raise ValueError(f"No numeric value found in '{raw}'")
    return float(match.group(0))


def normalize_int(raw: Any) -> int:
    val_float = normalize_float(raw)
    return int(val_float)


def normalize_bool(raw: Any) -> bool:
    if raw is None:
        raise ValueError("Cannot convert None to boolean")
    text = normalize_string(raw).lower()
    if text in ("true", "1", "yes", "y", "t", "active", "enabled", "on"):
        return True
    if text in ("false", "0", "no", "n", "f", "inactive", "disabled", "off"):
        return False
    raise ValueError(f"Cannot parse boolean from '{raw}'")


def normalize_date(raw: Any) -> str:
    if raw is None:
        raise ValueError("Cannot convert None to date")
    text = normalize_string(raw)
    date_formats = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%Y/%m/%d",
        "%B %d, %Y",
        "%b %d, %Y",
        "%Y-%m-%dT%H:%M:%S",
    ]
    for fmt in date_formats:
        try:
            dt = datetime.strptime(text, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    # If standard formats fail, check ISO 8601 substring
    iso_match = re.search(r"\b\d{4}-\d{2}-\d{2}\b", text)
    if iso_match:
        return iso_match.group(0)
    raise ValueError(f"Unable to parse date from '{raw}'")


def normalize_value(value: Any, expected_type: str) -> Any:
    """
    Deterministically normalizes a single value according to expected type string.
    """
    type_key = expected_type.strip().lower()
    if type_key in ("str", "string", "text"):
        return normalize_string(value)
    elif type_key in ("float", "double", "decimal", "number"):
        return normalize_float(value)
    elif type_key in ("int", "integer"):
        return normalize_int(value)
    elif type_key in ("bool", "boolean"):
        return normalize_bool(value)
    elif type_key in ("date", "datetime"):
        return normalize_date(value)
    else:
        # Fallback to string for unknown type spec
        return normalize_string(value)


def validate_and_normalize_record(
    raw_record: dict[str, Any],
    schema_definition: dict[str, str],
) -> tuple[bool, dict[str, Any], list[str]]:
    """
    Validates a single record against schema definition.
    Returns (is_valid, normalized_record, errors).
    """
    normalized: dict[str, Any] = {}
    errors: list[str] = []

    for field, field_type in schema_definition.items():
        if field not in raw_record:
            errors.append(f"Required field '{field}' is missing from extracted data")
            continue

        raw_val = raw_record[field]
        if raw_val is None or (isinstance(raw_val, str) and not raw_val.strip()):
            errors.append(f"Field '{field}' has empty or None value")
            continue

        try:
            norm_val = normalize_value(raw_val, field_type)
            normalized[field] = norm_val
        except (ValueError, TypeError) as ex:
            errors.append(f"Field '{field}' ({raw_val!r}) failed validation for type '{field_type}': {ex}")

    is_valid = len(errors) == 0
    return is_valid, normalized, errors


def validate_and_normalize_dataset(
    raw_data: Any,
    schema_definition: dict[str, str],
) -> tuple[bool, Any, list[str]]:
    """
    Validates either a single dictionary record or a list of dictionary records.
    Returns (is_valid, normalized_data, errors).
    """
    if raw_data is None:
        return False, None, ["Extracted data is None"]

    if isinstance(raw_data, list):
        if not raw_data:
            return False, [], ["Extracted dataset is an empty list; expected at least one row"]

        all_normalized = []
        all_errors = []
        for idx, row in enumerate(raw_data):
            if not isinstance(row, dict):
                all_errors.append(f"Row {idx} is not a valid object: {type(row)}")
                continue
            is_valid, norm_row, row_errors = validate_and_normalize_record(row, schema_definition)
            if not is_valid:
                for err in row_errors:
                    all_errors.append(f"Row {idx}: {err}")
            else:
                all_normalized.append(norm_row)

        return len(all_errors) == 0, all_normalized, all_errors

    elif isinstance(raw_data, dict):
        return validate_and_normalize_record(raw_data, schema_definition)

    else:
        return False, None, [f"Extracted data type {type(raw_data)} is neither dict nor list"]
