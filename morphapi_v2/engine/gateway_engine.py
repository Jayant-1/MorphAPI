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
from morphapi_v2.engine.type_coercer import type_coercer
from morphapi_v2.agent.deep_agent import deep_agent_v2

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
        prompt = request.prompt or ""
        target_url = request.target_url or getattr(request, "url", None) or ""
        if not prompt and target_url:
            prompt = f"Create an API extracting title, description, and link from {target_url}"

        logger.info("[GatewayEngineV2] Initiating LangGraph StateGraph synthesis for: '%s'", prompt)
        thread_id = f"thread_v2_{uuid.uuid4().hex[:12]}"

        initial_state = {
            "prompt": prompt,
            "target_url": target_url,
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
                    raw_results = results
                else:
                    raw_results = []
            else:
                # Hierarchical DOM or Custom Playwright JS extraction
                extract_res = await self.extractor.extract_with_plan(
                    page=page,
                    plan=plan,
                    target_schema=schema,
                    max_records=50,
                    runtime_params=params,
                )
                raw_results = extract_res.data or []

                # Auto-healing trigger if target website mutated and extraction returned 0 records
                if (not raw_results or len(raw_results) == 0) and plan.strategy == "hierarchical_dom":
                    logger.warning(
                        "[GatewayEngineV2] Extraction returned 0 records on active endpoint '%s' (Target site UI may have mutated). Triggering autonomous self-healing...",
                        slug,
                    )
                    healed_plan = await self.heal_endpoint(
                        user_id=user_id,
                        slug=slug,
                        target_url=resolved_url,
                        schema=schema,
                        previous_error=f"Container selector '{plan.container_selector}' matched 0 elements after website redesign",
                    )
                    if healed_plan:
                        # Re-extract immediately with the healed plan
                        retry_res = await self.extractor.extract_with_plan(
                            page=page,
                            plan=healed_plan,
                            target_schema=schema,
                            max_records=50,
                            runtime_params=params,
                        )
                        raw_results = retry_res.data or []
                        plan = healed_plan

            # 3. Shape Response according to Endpoint Contract
            response_shape = "list"
            if plan.contract and plan.contract.response_shape:
                response_shape = plan.contract.response_shape

            return type_coercer.shape_response(
                data=raw_results,
                response_shape=response_shape,
                query_params=params,
            )

    async def heal_endpoint(
        self,
        user_id: str,
        slug: str,
        target_url: str,
        schema: dict[str, str],
        previous_error: str,
    ) -> ContainerExtractionPlan | None:
        logger.info("[GatewayEngineV2] [SELF-HEALING] Investigating mutated page at '%s'...", target_url)
        healed_plan = await deep_agent_v2.autonomous_investigation(
            target_url=target_url,
            target_schema=schema,
            failure_context=previous_error,
            force_custom_script=True,
        )

        endpoint = await self.repo.get_endpoint(user_id=user_id, slug=slug)
        if endpoint:
            await self.repo.save_endpoint(
                endpoint_id=endpoint["endpoint_id"],
                user_id=user_id,
                api_name=endpoint["api_name"],
                slug=slug,
                target_url=target_url,
                schema_definition=endpoint["schema_definition"],
                inputs=endpoint["inputs"],
                plan=healed_plan.model_dump(),
                sample_data=endpoint["sample_data"],
                api_key=endpoint["api_key"],
            )
            logger.info("[GatewayEngineV2] [SELF-HEALING] Endpoint '%s' successfully healed and updated with strategy '%s'!", slug, healed_plan.strategy)
        return healed_plan


gateway_engine_v2 = MorphGatewayEngineV2()
