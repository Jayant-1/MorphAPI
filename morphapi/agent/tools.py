"""
MorphAPI Narrow Scoped Agent Tools
Only explicitly permitted, typed tools are exposed to the LLM agent.
Arbitrary shell execution, unrestricted network access, raw filesystem writes,
arbitrary SQL, and direct activate-endpoint tools are strictly disallowed.
"""

import json
import logging
from typing import Any, Callable, Coroutine
from pydantic import BaseModel, Field

from morphapi.browser.playwright_manager import PlaywrightManager
from morphapi.browser.page_inspector import PageInspector, EvidenceStore, prune_dom
from morphapi.browser.selector_tester import SelectorTester
from morphapi.browser.extractor import BrowserExtractor
from morphapi.browser.url_policy import UrlPolicyService, validate_selector_safety
from morphapi.services.validation_service import ValidationService
from morphapi.schemas.contracts import FieldEvidence, SelectorPatch
from morphapi.schemas.errors import FailureCode

logger = logging.getLogger("morphapi.agent_tools")


# --- Input Schemas ---

class InspectWebsiteInput(BaseModel):
    url: str = Field(..., description="Target policy-approved HTTP/HTTPS URL")
    scope_id: str | None = Field(default=None, description="Optional scope identifier")


class InspectElementContextInput(BaseModel):
    page_ref: str = Field(..., description="Evidence reference or target URL")
    region_hint: str | None = Field(default=None, description="CSS selector or container hint for the region")


class TestSelectorsInput(BaseModel):
    page_ref: str = Field(..., description="Target URL or page reference")
    candidates: dict[str, str] = Field(..., description="Dictionary mapping field name to candidate CSS/XPath selector")


class ExtractSampleDataInput(BaseModel):
    page_ref: str = Field(..., description="Target URL")
    selector_map: dict[str, str] = Field(..., description="Dictionary of candidate selectors")


class ValidateExtractionInput(BaseModel):
    schema_id: str = Field(..., description="Schema identifier or schema definition JSON")
    sample: dict[str, Any] = Field(..., description="Extracted sample data to validate")


class DiagnoseExtractionFailureInput(BaseModel):
    failure_id: str = Field(..., description="Failure identifier or endpoint ID")


class RequestCustomerClarificationInput(BaseModel):
    question: str = Field(..., description="Specific question to present to human operator")
    choices: list[str] = Field(default_factory=list, description="Available options or decisions")
    evidence_refs: list[str] = Field(default_factory=list, description="References to evidence files")


class SubmitCandidateConfigurationInput(BaseModel):
    draft_id: str = Field(..., description="Draft configuration or endpoint ID")
    selector_map: dict[str, str] = Field(..., description="Complete map of candidate selectors")
    rationale: str = Field(..., description="Agent reasoning explaining why these selectors are robust")
    evidence_refs: list[str] = Field(default_factory=list, description="Evidence references backing this proposal")


class GetEndpointStatusInput(BaseModel):
    endpoint_id: str = Field(..., description="Endpoint identifier")


# --- Tool Registry ---

class AgentToolRegistry:
    """
    Maintains and executes the narrow set of MorphAPI agent tools.
    """

    def __init__(
        self,
        browser_manager: PlaywrightManager | None = None,
        page_inspector: PageInspector | None = None,
        selector_tester: SelectorTester | None = None,
        browser_extractor: BrowserExtractor | None = None,
        validation_service: ValidationService | None = None,
        evidence_store: EvidenceStore | None = None,
        url_policy: UrlPolicyService | None = None,
        get_status_fn: Callable[[str], Coroutine[Any, Any, dict[str, Any]]] | None = None,
        get_failure_fn: Callable[[str], Coroutine[Any, Any, dict[str, Any]]] | None = None,
        get_schema_fn: Callable[[str], Coroutine[Any, Any, dict[str, str]]] | None = None,
    ):
        self.evidence_store = evidence_store or EvidenceStore()
        self.url_policy = url_policy or UrlPolicyService()
        self.browser_manager = browser_manager or PlaywrightManager(url_policy=self.url_policy)
        self.page_inspector = page_inspector or PageInspector(evidence_store=self.evidence_store)
        self.selector_tester = selector_tester or SelectorTester()
        self.browser_extractor = browser_extractor or BrowserExtractor(
            manager=self.browser_manager,
            inspector=self.page_inspector,
            tester=self.selector_tester,
            evidence_store=self.evidence_store,
        )
        self.validation_service = validation_service or ValidationService()
        self._get_status_fn = get_status_fn
        self._get_failure_fn = get_failure_fn
        self._get_schema_fn = get_schema_fn

    # 1. inspect_website
    async def inspect_website(self, url: str, scope_id: str | None = None) -> dict[str, Any]:
        """Inspects policy-approved website and returns evidence reference and DOM summary."""
        self.url_policy.enforce_url_policy(url)
        async with self.browser_manager.new_page_session(target_url=url) as page:
            await self.browser_manager.navigate_safely(page, url)
            result = await self.page_inspector.inspect(page, endpoint_id=scope_id or "default")
            return {
                "evidence_ref": result["evidence_ref"],
                "page_title": result["page_title"],
                "url": result["current_url"],
                "pruned_dom_sample": result["pruned_dom"][:45000],
                "screenshot_captured": result["screenshot_b64"] is not None,
            }

    # 2. inspect_element_context
    async def inspect_element_context(self, page_ref: str, region_hint: str | None = None) -> dict[str, Any]:
        """Returns focused structural DOM context around an element or region."""
        # Try reading from evidence store first
        evidence = self.evidence_store.load_evidence(page_ref)
        if evidence and "pruned_dom" in evidence:
            dom = evidence["pruned_dom"]
            return {"context_html": dom[:5000], "source": "evidence_store"}

        # Otherwise inspect live if page_ref is a URL
        if page_ref.startswith("http://") or page_ref.startswith("https://"):
            self.url_policy.enforce_url_policy(page_ref)
            async with self.browser_manager.new_page_session(target_url=page_ref) as page:
                await self.browser_manager.navigate_safely(page, page_ref)
                context = await self.page_inspector.inspect_element_context(page, region_hint=region_hint)
                return {"context_html": context, "source": "live_page"}

        return {"error": f"Invalid page_ref or evidence not found: {page_ref}"}

    # 3. test_selectors
    async def test_selectors(self, page_ref: str, candidates: dict[str, str]) -> dict[str, Any]:
        """Tests selectors against a real page and returns actual match counts and sample values."""
        target_url = page_ref
        if not (target_url.startswith("http://") or target_url.startswith("https://")):
            evidence = self.evidence_store.load_evidence(page_ref)
            if evidence and "url" in evidence:
                target_url = evidence["url"]
            else:
                return {"error": f"Unable to resolve target URL from page_ref: {page_ref}"}

        self.url_policy.enforce_url_policy(target_url)
        async with self.browser_manager.new_page_session(target_url=target_url) as page:
            await self.browser_manager.navigate_safely(page, target_url)
            evidences = await self.selector_tester.test_all_selectors(page, candidates)
            return {
                "field_evidences": [ev.model_dump() for ev in evidences],
                "all_matched": all(ev.matched_count > 0 for ev in evidences),
            }

    # 4. extract_sample_data
    async def extract_sample_data(self, page_ref: str, selector_map: dict[str, str]) -> dict[str, Any]:
        """Performs actual extraction in a real browser and returns raw samples."""
        target_url = page_ref
        if not (target_url.startswith("http://") or target_url.startswith("https://")):
            evidence = self.evidence_store.load_evidence(page_ref)
            if evidence and "url" in evidence:
                target_url = evidence["url"]
            else:
                return {"error": f"Unable to resolve target URL from page_ref: {page_ref}"}

        # Build schema mock from selector_map
        schema = {k: "str" for k in selector_map.keys()}
        res = await self.browser_extractor.extract("sample_check", target_url, schema, selector_map)
        return {
            "success": res.success,
            "sample_data": res.data,
            "error_code": res.error_code.value if res.error_code else None,
            "error_message": res.error_message,
        }

    # 5. validate_extraction
    async def validate_extraction(self, schema_id: str, sample: dict[str, Any]) -> dict[str, Any]:
        """Deterministically validates sample against customer schema definition."""
        schema: dict[str, str] = {}
        if self._get_schema_fn:
            schema = await self._get_schema_fn(schema_id)
        else:
            try:
                schema = json.loads(schema_id)
            except Exception:
                schema = {"default": "str"}

        val_result = self.validation_service.validate_extraction(sample, schema)
        return val_result.model_dump()

    # 6. diagnose_extraction_failure
    async def diagnose_extraction_failure(self, failure_id: str) -> dict[str, Any]:
        """Returns sanitized failure context and prior broken selectors."""
        if self._get_failure_fn:
            return await self._get_failure_fn(failure_id)
        return {
            "failure_id": failure_id,
            "diagnostic": "Selector matched 0 elements during scheduled extraction",
            "broken_field": "unknown",
        }

    # 7. request_customer_clarification
    async def request_customer_clarification(
        self,
        question: str,
        choices: list[str],
        evidence_refs: list[str],
    ) -> dict[str, Any]:
        """Registers a clarification prompt; pauses workflow for human input."""
        return {
            "status": "CLARIFICATION_REQUESTED",
            "question": question,
            "choices": choices,
            "evidence_refs": evidence_refs,
        }

    # 8. submit_candidate_configuration
    async def submit_candidate_configuration(
        self,
        draft_id: str,
        selector_map: dict[str, str],
        rationale: str,
        evidence_refs: list[str],
    ) -> dict[str, Any]:
        """
        Submits candidate configuration in non-active state for backend deterministic verification.
        The model cannot certify or activate configurations.
        """
        # Validate selector safety
        for k, sel in selector_map.items():
            is_safe, err = validate_selector_safety(sel)
            if not is_safe:
                return {
                    "accepted": False,
                    "error": f"Rejected candidate: unsafe selector '{sel}' for field '{k}': {err}",
                }

        return {
            "accepted": True,
            "draft_id": draft_id,
            "selector_map": selector_map,
            "rationale": rationale,
            "evidence_refs": evidence_refs,
            "status": "SUBMITTED_FOR_VERIFICATION",
        }

    # 9. get_endpoint_status
    async def get_endpoint_status(self, endpoint_id: str) -> dict[str, Any]:
        """Read-only query for endpoint status."""
        if self._get_status_fn:
            return await self._get_status_fn(endpoint_id)
        return {
            "endpoint_id": endpoint_id,
            "status": "HEALTHY",
            "active_version": 1,
        }

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        """Returns OpenAI-compatible tool specifications for the registered tools."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "inspect_website",
                    "description": "Inspects policy-approved URL and returns page title, DOM summary, and evidence reference",
                    "parameters": InspectWebsiteInput.model_json_schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "inspect_element_context",
                    "description": "Returns structural DOM context around an element or container region",
                    "parameters": InspectElementContextInput.model_json_schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "test_selectors",
                    "description": "Tests candidate CSS or XPath selectors in a real browser and returns match counts and sample values",
                    "parameters": TestSelectorsInput.model_json_schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "extract_sample_data",
                    "description": "Extracts sample data using candidate selector map in real browser",
                    "parameters": ExtractSampleDataInput.model_json_schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "validate_extraction",
                    "description": "Runs deterministic backend validation on extracted sample data",
                    "parameters": ValidateExtractionInput.model_json_schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "diagnose_extraction_failure",
                    "description": "Retrieves failure diagnostics and prior failing selectors",
                    "parameters": DiagnoseExtractionFailureInput.model_json_schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "request_customer_clarification",
                    "description": "Requests human operator clarification when multiple candidates are ambiguous",
                    "parameters": RequestCustomerClarificationInput.model_json_schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "submit_candidate_configuration",
                    "description": "Submits candidate selectors in non-active state for backend verification",
                    "parameters": SubmitCandidateConfigurationInput.model_json_schema(),
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_endpoint_status",
                    "description": "Read-only lookup for endpoint status",
                    "parameters": GetEndpointStatusInput.model_json_schema(),
                },
            },
        ]
