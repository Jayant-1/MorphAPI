"""
MorphAPI Deterministic Validation Service
Validates extracted field values against user schema using Pydantic v2 and explicit type coercion rules.
Never hallucinates or synthesizes missing values.
"""

import re
from datetime import datetime
from typing import Any, Tuple
from pydantic import BaseModel, create_model

from morphapi.schemas.contracts import ValidationResult, FieldEvidence

CURRENCY_REGEX = re.compile(r"[\$,€,£,¥,\s]")


class ValidationService:
    """
    Deterministic validator ensuring extracted values strictly adhere to customer schema definitions.
    """

    def normalize_field_value(self, raw_value: Any, expected_type: str) -> Tuple[Any, str | None]:
        """
        Normalizes and coerces a single field value to its expected type.
        Returns (coerced_value, error_message).
        """
        if raw_value is None:
            return None, "Value is null or missing"

        type_lower = expected_type.lower().strip()

        # String / text
        if type_lower in ("str", "string", "text"):
            val_str = str(raw_value).strip()
            if not val_str:
                return None, "Empty string value"
            return val_str, None

        # Integer
        elif type_lower in ("int", "integer"):
            val_str = str(raw_value).strip()
            # Remove commas or currency symbols
            cleaned = CURRENCY_REGEX.sub("", val_str)
            try:
                # Handle possible float string e.g. "12.0"
                return int(float(cleaned)), None
            except (ValueError, TypeError):
                return None, f"Cannot convert '{val_str}' to integer"

        # Float / number
        elif type_lower in ("float", "number", "decimal"):
            val_str = str(raw_value).strip()
            cleaned = CURRENCY_REGEX.sub("", val_str)
            try:
                return float(cleaned), None
            except (ValueError, TypeError):
                return None, f"Cannot convert '{val_str}' to float"

        # Boolean
        elif type_lower in ("bool", "boolean"):
            val_str = str(raw_value).strip().lower()
            if val_str in ("true", "yes", "1", "in stock", "available", "active"):
                return True, None
            elif val_str in ("false", "no", "0", "out of stock", "unavailable", "inactive"):
                return False, None
            return None, f"Cannot convert '{raw_value}' to boolean"

        # Date / datetime
        elif type_lower in ("date", "datetime"):
            val_str = str(raw_value).strip()
            # Try ISO formats and standard web formats
            formats = [
                "%Y-%m-%d",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S",
                "%m/%d/%Y",
                "%d-%m-%Y",
                "%B %d, %Y",
                "%b %d, %Y",
            ]
            for fmt in formats:
                try:
                    dt = datetime.strptime(val_str, fmt)
                    return dt.strftime("%Y-%m-%d"), None
                except ValueError:
                    continue
            return None, f"Cannot parse date format from '{val_str}'"

        # Default fallback
        return str(raw_value).strip(), None

    def validate_record(
        self,
        record: dict[str, Any],
        schema_definition: dict[str, str],
    ) -> Tuple[dict[str, Any] | None, list[str]]:
        """
        Validates and normalizes a single dictionary record against schema_definition.
        """
        normalized: dict[str, Any] = {}
        errors: list[str] = []

        for field_name, expected_type in schema_definition.items():
            if field_name not in record or record[field_name] is None:
                errors.append(f"Field '{field_name}' is missing from record")
                continue

            raw_val = record[field_name]
            coerced_val, err = self.normalize_field_value(raw_val, expected_type)
            if err:
                errors.append(f"Field '{field_name}' failed validation: {err}")
            else:
                normalized[field_name] = coerced_val

        if errors:
            return None, errors
        return normalized, []

    def validate_extraction(
        self,
        extracted_data: Any,
        schema_definition: dict[str, str],
        field_evidences: list[FieldEvidence] | None = None,
    ) -> ValidationResult:
        """
        Validates extracted data (either a single record or list of records).
        """
        evidences = field_evidences or []

        if extracted_data is None:
            return ValidationResult(
                is_valid=False,
                normalized_data=None,
                errors=["No data extracted to validate"],
                field_evidences=evidences,
            )

        if isinstance(extracted_data, list):
            if not extracted_data:
                return ValidationResult(
                    is_valid=False,
                    normalized_data=[],
                    errors=["Extracted list contains 0 items"],
                    field_evidences=evidences,
                )

            normalized_list = []
            all_errors: list[str] = []
            for idx, item in enumerate(extracted_data):
                if not isinstance(item, dict):
                    all_errors.append(f"Row {idx} is not a dictionary")
                    continue
                norm_record, errs = self.validate_record(item, schema_definition)
                if errs:
                    all_errors.extend([f"Row {idx}: {e}" for e in errs])
                else:
                    normalized_list.append(norm_record)

            if all_errors:
                return ValidationResult(
                    is_valid=False,
                    normalized_data=None,
                    errors=all_errors,
                    field_evidences=evidences,
                )
            return ValidationResult(
                is_valid=True,
                normalized_data=normalized_list,
                errors=[],
                field_evidences=evidences,
            )

        elif isinstance(extracted_data, dict):
            norm_record, errs = self.validate_record(extracted_data, schema_definition)
            if errs:
                return ValidationResult(
                    is_valid=False,
                    normalized_data=None,
                    errors=errs,
                    field_evidences=evidences,
                )
            return ValidationResult(
                is_valid=True,
                normalized_data=norm_record,
                errors=[],
                field_evidences=evidences,
            )

        return ValidationResult(
            is_valid=False,
            normalized_data=None,
            errors=[f"Unsupported data structure: {type(extracted_data)}"],
            field_evidences=evidences,
        )
