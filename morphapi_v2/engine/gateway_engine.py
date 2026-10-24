"""
Core Gateway Engine for MorphAPI V2
Orchestrates Intent Parsing, Network Sniffing, DOM Cluster Analysis,
Hierarchical Extraction, and Semantic Verification via LangGraph Durable Workflows.
"""

import logging
import uuid
from typing import Any
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from morphapi_v2.schemas.models import (
    EndpointV2CreateRequest,
    EndpointV2Response,
    ContainerExtractionPlan,
)
from morphapi_v2.browser.session_manager import session_manager_v2
from morphapi_v2.browser.network_sniffer import NetworkSniffer
from morphapi_v2.browser.hierarchical_extractor import hierarchical_extractor
from morphapi_v2.workflows.graph import morphapi_workflow_v2
from morphapi_v2.db.repository import endpoint_repo_v2

logger = logging.getLogger("morphapi_v2.gateway")


class MorphGatewayEngineV2:
    def __init__(self):
        self.workflow = morphapi_workflow_v2
        self.repo = endpoint_repo_v2
        self.session_manager = session_manager_v2
        self.extractor = hierarchical_extractor

    async def create_endpoint(self, request: EndpointV2CreateRequest) -> EndpointV2Response:
        """
        Executes LangGraph durable workflow:
        START -> parse_intent -> inspect_and_sniff -> propose_plan (Deep Agent LLM) ->
        test_extraction -> validate_results -> (if needed: reflect_and_heal) -> activate_endpoint -> END
        """
        logger.info("[GatewayEngineV2] Initiating LangGraph StateGraph synthesis for: '%s'", request.prompt)
        thread_id = f"thread_v2_{uuid.uuid4().hex[:12]}"

        initial_state = {
            "prompt": request.prompt,
            "target_url": request.target_url or "",
            "name": request.name,
            "user_id": request.user_id,
            "intent": {},
            "inspection_url": "",
            "raw_html": "",
            "intercepted_api": None,
            "plan": None,
            "extracted_data": None,
            "is_verified": False,
            "validation_issues": [],
            "turn": 1,
            "max_turns": 3,
            "status": "INITIALIZING",
            "error_message": None,
            "final_response": None,
        }

        final_state = await self.workflow.graph.ainvoke(
            initial_state,
            config={"configurable": {"thread_id": thread_id}},
        )

        if final_state.get("status") != "ACTIVE" or not final_state.get("final_response"):
            err = final_state.get("error_message") or "; ".join(final_state.get("validation_issues", ["Extraction verification failed"]))
            raise RuntimeError(f"LangGraph Workflow failed to activate endpoint: {err}")

        return EndpointV2Response(**final_state["final_response"])

    async def execute_query(
        self,
        user_id: str,
        slug: str,
        query_params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        endpoint = await self.repo.get_endpoint(user_id=user_id, slug=slug)
        if not endpoint:
            raise KeyError(f"Endpoint '{slug}' not found for user '{user_id}'")

        target_template = endpoint["target_url"]
        schema = endpoint["schema_definition"]
        plan_dict = endpoint["plan"]
        plan = ContainerExtractionPlan(**plan_dict)
        params = query_params or {}

        # 1. Resolve parameterized URL
        resolved_url = target_template
        for k, v in params.items():
            if f"{{{k}}}" in resolved_url:
                resolved_url = resolved_url.replace(f"{{{k}}}", str(v))

        # If any placeholders remain unresolved, strip them or use defaults
        if "{" in resolved_url:
            parsed = urlparse(resolved_url)
            if "{" in parsed.query:
                qs = parse_qs(parsed.query)
                clean_qs = {k: [v for v in vals if "{" not in v] for k, vals in qs.items()}
                clean_qs = {k: v for k, v in clean_qs.items() if v}
                new_q = urlencode(clean_qs, doseq=True)
                resolved_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_q, parsed.fragment))

        # 2. Extract Data using Active Plan (Fast Path: Zero LLM / Zero Graph calls)
        async with self.session_manager.new_page_session() as page:
            sniffer = NetworkSniffer(target_fields=list(schema.keys()))
            sniffer.attach(page)

            await self.session_manager.navigate_and_stabilize(page, resolved_url)

            if plan.strategy == "intercepted_api":
                best_api = sniffer.get_best_match()
                if best_api and best_api["records"]:
                    results = []
                    for rec in best_api["records"][:30]:
                        row = {}
                        for target_k, mapped_k in plan.intercepted_field_map.items():
                            row[target_k] = rec.get(mapped_k)
                        results.append(row)
                    return results

            # Hierarchical DOM extraction
            extract_res = await self.extractor.extract_with_plan(
                page=page,
                plan=plan,
                target_schema=schema,
                max_records=50,
            )
            return extract_res.data or []


gateway_engine_v2 = MorphGatewayEngineV2()
