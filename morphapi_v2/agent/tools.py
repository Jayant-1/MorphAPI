"""
Typed Tools Registry for MorphAPI V2 Deep Agent
Gives the agent explicit, narrow, typed tools to inspect, sniff, cluster, test, validate, and submit plans.
"""

import json
import logging
import re
from typing import Any
from pydantic import BaseModel, Field

from morphapi_v2.browser.session_manager import session_manager_v2
from morphapi_v2.browser.network_sniffer import NetworkSniffer
from morphapi_v2.browser.dom_cluster import dom_cluster_analyzer
from morphapi_v2.browser.hierarchical_extractor import hierarchical_extractor
from morphapi_v2.engine.semantic_validator import semantic_validator_v2
from morphapi_v2.schemas.models import ContainerExtractionPlan, RelativeFieldSelector

logger = logging.getLogger("morphapi_v2.tools")


# --- Tool Input Schemas ---

class InspectPageInput(BaseModel):
    url: str = Field(..., description="Target HTTP/HTTPS URL to inspect and stabilize in Chromium")


class CheckNetworkApiInput(BaseModel):
    target_fields: list[str] = Field(..., description="List of schema field names to match against intercepted JSON APIs")


class AnalyzeDomClustersInput(BaseModel):
    target_schema: dict[str, str] = Field(..., description="Target schema definition mapping field names to types")


class TestHierarchicalSelectorsInput(BaseModel):
    container_selector: str = Field(..., description="CSS/XPath selector matching repeating record blocks")
    field_rules: dict[str, dict[str, str]] = Field(
        ...,
        description="Map of field name to {'selector': relative_css, 'attribute': 'text'|'href'|'src'}"
    )


class ValidateSampleDataInput(BaseModel):
    sample_records: list[dict[str, Any]] = Field(..., description="Extracted sample records to validate")
    schema_definition: dict[str, str] = Field(..., description="Target schema definition")


class SubmitExtractionPlanInput(BaseModel):
    strategy: str = Field(default="hierarchical_dom", description="'hierarchical_dom' or 'intercepted_api'")
    container_selector: str = Field(..., description="Verified container selector")
    field_rules: dict[str, dict[str, str]] = Field(..., description="Verified field extraction rules")
    rationale: str = Field(..., description="Reasoning explaining why this configuration is reliable")


# --- Tool Registry ---

class AgentToolRegistryV2:
    def __init__(self):
        self.session_manager = session_manager_v2
        self.dom_cluster = dom_cluster_analyzer
        self.extractor = hierarchical_extractor
        self.validator = semantic_validator_v2
        self.cached_page_html: str = ""
        self.cached_page_url: str = ""
        self.cached_sniffer: NetworkSniffer | None = None

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        """Returns standard OpenAI / NIM function-calling tool schemas."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "inspect_page",
                    "description": "Loads the webpage in Chromium, waits for SPA hydration/network stabilization, and returns sanitized DOM content without scripts or styles.",
                    "parameters": InspectPageInput.model_json_schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "check_sniffed_network_api",
                    "description": "Checks if any internal JSON APIs (Algolia search, REST, GraphQL) were intercepted during page load that match the desired fields.",
                    "parameters": CheckNetworkApiInput.model_json_schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_dom_clusters",
                    "description": "Runs DOM cluster analysis on cleaned HTML to automatically discover candidate repeating cards, tables, and relative child selectors.",
                    "parameters": AnalyzeDomClustersInput.model_json_schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "test_hierarchical_selectors",
                    "description": "Tests a candidate container selector and relative field selectors live in Chromium, returning match count and sample values.",
                    "parameters": TestHierarchicalSelectorsInput.model_json_schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "validate_sample_data",
                    "description": "Validates sample extracted data against semantic gates: checks diversity, non-empty coverage, and rejects navigation links.",
                    "parameters": ValidateSampleDataInput.model_json_schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "submit_extraction_plan",
                    "description": "Submits the verified extraction plan to the gateway for activation.",
                    "parameters": SubmitExtractionPlanInput.model_json_schema(),
                },
            },
        ]

    async def inspect_page(self, url: str) -> dict[str, Any]:
        logger.info("[Tool: inspect_page] Navigating to '%s'", url)
        self.cached_page_url = url
        sniffer = NetworkSniffer()
        self.cached_sniffer = sniffer

        async with self.session_manager.new_page_session() as page:
            sniffer.attach(page)
            await self.session_manager.navigate_and_stabilize(page, url)
            raw_html = await page.content()
            self.cached_page_html = raw_html

            clean_soup = self.dom_cluster.clean_html(raw_html)
            content_root = (
                clean_soup.find(["main", "article"])
                or clean_soup.find(id=re.compile(r"content|app|root", re.I))
                or clean_soup.body
                or clean_soup
            )
            title = await page.title()
            return {
                "title": title,
                "url": page.url,
                "cleaned_html_sample": str(content_root)[:8000],
                "total_html_length": len(raw_html),
            }

    async def check_sniffed_network_api(self, target_fields: list[str]) -> dict[str, Any]:
        logger.info("[Tool: check_sniffed_network_api] Checking intercepted APIs for fields: %s", target_fields)
        if not self.cached_sniffer:
            return {"found": False, "message": "No active page inspection session found. Run inspect_page first."}

        self.cached_sniffer.target_fields = [f.lower().replace("_", "") for f in target_fields]
        best_api = self.cached_sniffer.get_best_match()
        if not best_api:
            return {"found": False, "message": "No internal JSON API match found. Use DOM selector analysis."}

        return {
            "found": True,
            "api_url": best_api["url"],
            "path": best_api["path"],
            "score": best_api["score"],
            "field_mapping": best_api["field_mapping"],
            "sample_record": best_api["records"][0] if best_api["records"] else {},
            "total_records": len(best_api["records"]),
        }

    async def analyze_dom_clusters(self, target_schema: dict[str, str]) -> dict[str, Any]:
        logger.info("[Tool: analyze_dom_clusters] Analyzing layout for schema: %s", target_schema)
        if not self.cached_page_html:
            return {"error": "Page HTML not available. Run inspect_page first."}

        plan = self.dom_cluster.analyze_dom(
            html_content=self.cached_page_html,
            target_schema=target_schema,
            target_url=self.cached_page_url,
        )
        if not plan:
            return {"found": False, "message": "No standard repeating clusters found. Analyze DOM manually."}

        return {
            "found": True,
            "strategy": plan.strategy,
            "container_selector": plan.container_selector,
            "field_rules": {
                k: {"selector": v.selector, "attribute": v.attribute}
                for k, v in plan.field_rules.items()
            },
            "discovery_method": plan.discovery_method,
            "confidence_score": plan.confidence_score,
        }

    async def test_hierarchical_selectors(
        self,
        container_selector: str,
        field_rules: dict[str, dict[str, str]],
    ) -> dict[str, Any]:
        logger.info("[Tool: test_hierarchical_selectors] Testing container: '%s'", container_selector)
        if not self.cached_page_url:
            return {"error": "No target URL. Run inspect_page first."}

        typed_rules = {}
        for k, v in field_rules.items():
            typed_rules[k] = RelativeFieldSelector(
                selector=v.get("selector", "."),
                attribute=v.get("attribute", "text"),
            )

        plan = ContainerExtractionPlan(
            strategy="hierarchical_dom",
            container_selector=container_selector,
            field_rules=typed_rules,
        )

        async with self.session_manager.new_page_session() as page:
            await self.session_manager.navigate_and_stabilize(page, self.cached_page_url)
            res = await self.extractor.extract_with_plan(
                page=page,
                plan=plan,
                target_schema={k: "str" for k in field_rules.keys()},
                max_records=10,
            )

            return {
                "success": res.success,
                "matched_count": res.count,
                "sample_data": res.data[:3] if res.data else [],
                "error": res.error_message,
            }

    async def validate_sample_data(
        self,
        sample_records: list[dict[str, Any]],
        schema_definition: dict[str, str],
    ) -> dict[str, Any]:
        logger.info("[Tool: validate_sample_data] Validating %d records", len(sample_records))
        is_valid, issues = self.validator.validate_dataset(sample_records, schema_definition)
        return {
            "is_valid": is_valid,
            "issues": issues,
            "checked_records": len(sample_records),
        }

    async def submit_extraction_plan(
        self,
        strategy: str,
        container_selector: str,
        field_rules: dict[str, dict[str, str]],
        rationale: str,
    ) -> dict[str, Any]:
        logger.info("[Tool: submit_extraction_plan] Submitting plan with container: '%s'", container_selector)
        typed_rules = {
            k: RelativeFieldSelector(
                selector=v.get("selector", "."),
                attribute=v.get("attribute", "text"),
            )
            for k, v in field_rules.items()
        }

        plan = ContainerExtractionPlan(
            strategy=strategy,
            container_selector=container_selector,
            field_rules=typed_rules,
            rationale=rationale,
            discovery_method="deep_agent_tools",
            confidence_score=0.95,
        )
        return {
            "accepted": True,
            "plan": plan.model_dump(),
        }


tool_registry_v2 = AgentToolRegistryV2()
