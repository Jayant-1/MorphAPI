"""
Type Coercer and Response Normalizer for MorphAPI V2
Transforms raw scraped strings into typed scalars (int, float, bool, url, list)
and structures output responses according to endpoint contracts (list, single_object, paginated).
"""

import re
from typing import Any
from urllib.parse import urljoin


class TypeCoercer:
    """
    Normalizes and coerces raw extracted string data into strongly typed Python values.
    """

    @staticmethod
    def coerce_field(
        value: Any,
        target_type: str = "str",
        clean_regex: str | None = None,
        default: Any = None,
        base_url: str = "",
    ) -> Any:
        if value is None:
            return default

        # If already matching typed container (e.g. parsed list or dict)
        if target_type in ("list", "list[str]", "array") and isinstance(value, list):
            return [str(x).strip() for x in value if str(x).strip()]

        val_str = str(value).strip()

        # Optional regex extraction
        if clean_regex:
            match = re.search(clean_regex, val_str)
            if match:
                val_str = match.group(0).strip()

        t = target_type.lower().strip()

        if t in ("int", "integer"):
            # Extract digits while ignoring commas and units (e.g. "165 points", "$3,500" -> 165, 3500)
            cleaned = val_str.replace(",", "")
            m = re.search(r"-?\d+", cleaned)
            if m:
                try:
                    return int(m.group(0))
                except ValueError:
                    pass
            return default if default is not None else 0

        elif t in ("float", "number"):
            # Extract decimals while ignoring currency and text (e.g. "$1,299.99", "4.8 / 5" -> 1299.99, 4.8)
            cleaned = re.sub(r"[$€£¥,]", "", val_str)
            m = re.search(r"-?\d+(?:\.\d+)?", cleaned)
            if m:
                try:
                    return float(m.group(0))
                except ValueError:
                    pass
            return default if default is not None else 0.0

        elif t in ("bool", "boolean"):
            lowered = val_str.lower()
            if lowered in ("true", "1", "yes", "in stock", "available", "active", "y", "verified"):
                return True
            if lowered in ("false", "0", "no", "out of stock", "unavailable", "inactive", "n", ""):
                return False
            return bool(val_str)

        elif t in ("list[str]", "list", "array"):
            if not val_str:
                return []
            parts = re.split(r"[,|•;\n]", val_str)
            return [p.strip() for p in parts if p.strip()]

        elif t in ("url", "uri"):
            if not val_str:
                return ""
            if base_url and not val_str.startswith(("http://", "https://", "mailto:", "tel:")):
                return urljoin(base_url, val_str)
            return val_str

        # Default string type
        return val_str

    @classmethod
    def coerce_record(
        cls,
        record: dict[str, Any],
        field_specs: dict[str, Any],
        base_url: str = "",
    ) -> dict[str, Any]:
        """Coerces a single record dictionary according to field specifications."""
        coerced: dict[str, Any] = {}
        for k, v in record.items():
            spec = field_specs.get(k, "str")
            if isinstance(spec, str):
                target_type = spec
                regex = None
                default = None
            elif isinstance(spec, dict):
                target_type = spec.get("target_type") or spec.get("type") or "str"
                regex = spec.get("clean_regex")
                default = spec.get("default")
            elif hasattr(spec, "target_type"):
                target_type = spec.target_type
                regex = getattr(spec, "clean_regex", None)
                default = getattr(spec, "default", None)
            else:
                target_type = "str"
                regex = None
                default = None

            coerced[k] = cls.coerce_field(
                value=v,
                target_type=target_type,
                clean_regex=regex,
                default=default,
                base_url=base_url,
            )
        return coerced

    @classmethod
    def coerce_dataset(
        cls,
        dataset: list[dict[str, Any]],
        field_specs: dict[str, Any],
        base_url: str = "",
    ) -> list[dict[str, Any]]:
        """Coerces an entire list of record dictionaries."""
        if not dataset:
            return []
        return [cls.coerce_record(row, field_specs, base_url) for row in dataset]

    @classmethod
    def shape_response(
        cls,
        data: list[dict[str, Any]] | dict[str, Any],
        response_shape: str = "list",
        query_params: dict[str, Any] | None = None,
        total_count: int | None = None,
    ) -> Any:
        """
        Structures extracted data into the requested response shape:
        - "list": returns standard array of records
        - "single_object": returns a single entity object
        - "paginated": returns an envelope with page, limit, count, and data array
        """
        params = query_params or {}

        if response_shape == "single_object":
            if isinstance(data, list):
                return data[0] if data else {}
            return data if isinstance(data, dict) else {}

        # If data is a single dict but caller expects list
        records = [data] if isinstance(data, dict) else (data or [])

        if response_shape == "paginated":
            try:
                page = int(params.get("page", 1))
            except (ValueError, TypeError):
                page = 1
            try:
                limit = int(params.get("limit", 20))
            except (ValueError, TypeError):
                limit = 20

            count = len(records)
            total = total_count if total_count is not None else count

            return {
                "page": page,
                "limit": limit,
                "count": count,
                "total": total,
                "has_more": count >= limit,
                "data": records,
            }

        return records


type_coercer = TypeCoercer()
