"""
Semantic Validation Gate for MorphAPI V2
Ensures extracted records are genuinely meaningful content and strictly rejects
navigation bars, footer links, duplicate boilerplate, and unaligned data.
"""

import logging
from urllib.parse import urlparse
from typing import Any

logger = logging.getLogger("morphapi_v2.validator")

NAVIGATION_PATHS = {
    "/", "/about", "/about/", "/contact", "/contact/", "/apply", "/apply/",
    "/interviews", "/interviews/", "/faq", "/faq/", "/terms", "/terms/",
    "/privacy", "/privacy/", "/login", "/login/", "/signin", "/register",
    "/signup", "/blog", "/blog/", "/press", "/jobs", "/careers", "/help",
    "/support", "/pricing", "/status",
}


class SemanticValidatorV2:
    def __init__(
        self,
        min_diversity_ratio: float = 0.5,
        min_primary_coverage: float = 0.6,
    ):
        self.min_diversity_ratio = min_diversity_ratio
        self.min_primary_coverage = min_primary_coverage

    def validate_dataset(
        self,
        dataset: list[dict[str, Any]] | None,
        schema_definition: dict[str, str],
    ) -> tuple[bool, list[str]]:
        issues: list[str] = []

        if not dataset or not isinstance(dataset, list):
            return False, ["Dataset is empty or not a list of records"]

        total_rows = len(dataset)
        if total_rows == 0:
            return False, ["Extracted 0 records"]

        # Identify primary identifying field (e.g. company_name, name, title)
        primary_field = None
        for k in schema_definition.keys():
            if any(term in k.lower() for term in ("name", "title", "company", "headline")):
                primary_field = k
                break
        if not primary_field:
            primary_field = list(schema_definition.keys())[0]

        # 1. Primary Field Coverage Check
        primary_values = [r.get(primary_field) for r in dataset if r.get(primary_field)]
        coverage = len(primary_values) / total_rows
        if coverage < self.min_primary_coverage:
            issues.append(
                f"Primary field '{primary_field}' has low coverage: {coverage:.1%} "
                f"(expected >= {self.min_primary_coverage:.1%})"
            )

        # 2. Diversity / Cardinality Check (Preventing repeated navbar text)
        if total_rows >= 3 and primary_values:
            unique_primary = set(str(v).strip().lower() for v in primary_values)
            diversity = len(unique_primary) / len(primary_values)
            if diversity < self.min_diversity_ratio:
                issues.append(
                    f"Low value diversity on primary field '{primary_field}': {diversity:.1%} unique values. "
                    f"Matches repetitive page boilerplate or navigation."
                )

        # 3. Navigational Link Blacklist Check
        link_fields = [k for k in schema_definition.keys() if any(term in k.lower() for term in ("link", "url", "href"))]
        for lf in link_fields:
            links = [r.get(lf) for r in dataset if r.get(lf)]
            if links:
                nav_count = 0
                for link in links:
                    parsed = urlparse(str(link))
                    path = parsed.path.rstrip("/")
                    if not path:
                        path = "/"
                    if path.lower() in NAVIGATION_PATHS:
                        nav_count += 1

                nav_ratio = nav_count / len(links)
                if nav_ratio >= 0.5:
                    issues.append(
                        f"Field '{lf}' contains {nav_ratio:.1%} website navigation links "
                        f"(e.g. {links[:3]}). Rejection: Content links expected, not navigation chrome."
                    )

        is_valid = len(issues) == 0
        if not is_valid:
            logger.warning("[SemanticValidatorV2] Validation rejected dataset: %s", issues)
        else:
            logger.info("[SemanticValidatorV2] Validation passed for %d records against schema: %s", total_rows, schema_definition)

        return is_valid, issues


semantic_validator_v2 = SemanticValidatorV2()
