"""
LangGraph Durable Workflow for MorphAPI V2
Orchestrates Intent Parsing, Browser Inspection, Deep Agent LLM Planning,
Hierarchical Testing, Semantic Validation, and Self-Healing.
"""

import hashlib
import logging
import secrets
from typing import Any
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from morphapi_v2.workflows.state import WorkflowStateV2
from morphapi_v2.engine.intent_parser import intent_parser_v2
from morphapi_v2.browser.session_manager import session_manager_v2
from morphapi_v2.browser.network_sniffer import NetworkSniffer
from morphapi_v2.browser.hierarchical_extractor import hierarchical_extractor
from morphapi_v2.agent.deep_agent import deep_agent_v2
from morphapi_v2.engine.semantic_validator import semantic_validator_v2
from morphapi_v2.db.repository import endpoint_repo_v2
from morphapi_v2.schemas.models import ContainerExtractionPlan, EndpointV2Response

logger = logging.getLogger("morphapi_v2.workflow")


class MorphApiWorkflowV2:
    def __init__(self):
        self.checkpointer = MemorySaver()
        self.graph = self._compile_graph()

    def _compile_graph(self):
        builder = StateGraph(WorkflowStateV2)

        # 1. Register Graph Nodes
        builder.add_node("parse_intent", self._parse_intent_node)
        builder.add_node("inspect_and_sniff", self._inspect_and_sniff_node)
        builder.add_node("propose_plan", self._propose_plan_node)
        builder.add_node("test_extraction", self._test_extraction_node)
        builder.add_node("validate_results", self._validate_results_node)
        builder.add_node("reflect_and_heal", self._reflect_and_heal_node)
        builder.add_node("activate_endpoint", self._activate_endpoint_node)
        builder.add_node("mark_failed", self._mark_failed_node)

        # 2. Wire Linear Flow
        builder.add_edge(START, "parse_intent")
        builder.add_edge("parse_intent", "inspect_and_sniff")
        builder.add_edge("inspect_and_sniff", "propose_plan")
        builder.add_edge("propose_plan", "test_extraction")
        builder.add_edge("test_extraction", "validate_results")

        # 3. Validation Decision: Verified -> Activate, Else -> Self-heal or Fail
        builder.add_conditional_edges(
            "validate_results",
            self.route_validation,
            {
                "activate_endpoint": "activate_endpoint",
                "reflect_and_heal": "reflect_and_heal",
                "mark_failed": "mark_failed",
            },
        )

        builder.add_edge("reflect_and_heal", "test_extraction")
        builder.add_edge("activate_endpoint", END)
        builder.add_edge("mark_failed", END)

        return builder.compile(checkpointer=self.checkpointer)

    def route_validation(self, state: WorkflowStateV2) -> str:
        if state.get("is_verified", False):
            return "activate_endpoint"
        if state.get("turn", 1) < state.get("max_turns", 3):
            return "reflect_and_heal"
        return "mark_failed"

    # --- Graph Node Implementations ---

    async def _parse_intent_node(self, state: WorkflowStateV2) -> dict[str, Any]:
        logger.info("[LangGraph V2] [NODE: parse_intent] Parsing prompt: '%s'", state["prompt"])
        intent = intent_parser_v2.parse(
            prompt=state["prompt"],
            target_url=state.get("target_url"),
            name=state.get("name"),
        )
        return {
            "intent": intent.model_dump(),
            "target_url": intent.target_url_template,
            "inspection_url": intent.sample_inspection_url,
            "status": "INSPECTING",
            "turn": 1,
            "max_turns": state.get("max_turns", 3),
        }

    async def _inspect_and_sniff_node(self, state: WorkflowStateV2) -> dict[str, Any]:
        url = state["inspection_url"]
        schema = state["intent"]["schema_definition"]
        logger.info("[LangGraph V2] [NODE: inspect_and_sniff] Navigating to '%s'", url)

        async with session_manager_v2.new_page_session() as page:
            sniffer = NetworkSniffer(target_fields=list(schema.keys()))
            sniffer.attach(page)

            await session_manager_v2.navigate_and_stabilize(page, url)
            html = await page.content()
            best_api = sniffer.get_best_match()

            return {
                "raw_html": html,
                "intercepted_api": best_api,
                "status": "PROPOSING",
            }

    async def _propose_plan_node(self, state: WorkflowStateV2) -> dict[str, Any]:
        logger.info("[LangGraph V2] [NODE: propose_plan] Generating proposal...")
        schema = state["intent"]["schema_definition"]
        intercepted = state.get("intercepted_api")

        # Fast path if API sniffer intercepted Algolia/REST cleanly
        if intercepted and intercepted["score"] >= 0.6:
            logger.info("[LangGraph V2] Intercepted internal API feed: '%s'", intercepted["url"])
            plan = ContainerExtractionPlan(
                strategy="intercepted_api",
                container_selector="network_api",
                intercepted_api_url_pattern=intercepted["url"],
                intercepted_hits_path=intercepted["path"],
                intercepted_field_map=intercepted["field_mapping"],
                confidence_score=intercepted["score"],
                discovery_method="network_sniffer",
                rationale=f"Captured clean internal JSON data feed at '{intercepted['url']}'",
            )
            return {"plan": plan.model_dump(), "status": "TESTING"}

        # Deep Agent Autonomous Investigation (Model chooses when to use which tool)
        plan = await deep_agent_v2.autonomous_investigation(
            target_url=state["inspection_url"],
            target_schema=schema,
        )
        logger.info("[LangGraph V2] Deep Agent proposed container: '%s'", plan.container_selector)
        return {"plan": plan.model_dump(), "status": "TESTING"}

    async def _test_extraction_node(self, state: WorkflowStateV2) -> dict[str, Any]:
        logger.info("[LangGraph V2] [NODE: test_extraction] Testing extraction in live browser...")
        plan = ContainerExtractionPlan(**state["plan"])
        schema = state["intent"]["schema_definition"]

        # If intercepted API strategy
        if plan.strategy == "intercepted_api":
            intercepted = state.get("intercepted_api") or {}
            records = intercepted.get("records", [])
            mapping = plan.intercepted_field_map
            dataset = []
            for rec in records[:25]:
                row = {k: rec.get(v) for k, v in mapping.items()}
                dataset.append(row)
            return {"extracted_data": dataset, "status": "VALIDATING"}

        # Hierarchical live browser extraction
        async with session_manager_v2.new_page_session() as page:
            await session_manager_v2.navigate_and_stabilize(page, state["inspection_url"])
            res = await hierarchical_extractor.extract_with_plan(
                page=page,
                plan=plan,
                target_schema=schema,
                max_records=25,
            )
            return {"extracted_data": res.data or [], "status": "VALIDATING"}

    async def _validate_results_node(self, state: WorkflowStateV2) -> dict[str, Any]:
        logger.info("[LangGraph V2] [NODE: validate_results] Running semantic validation...")
        schema = state["intent"]["schema_definition"]
        dataset = state.get("extracted_data") or []

        is_valid, issues = semantic_validator_v2.validate_dataset(dataset, schema)
        logger.info("[LangGraph V2] Validation outcome: %s (Issues: %s)", is_valid, issues)

        return {
            "is_verified": is_valid,
            "validation_issues": issues,
            "status": "VERIFIED" if is_valid else "HEALING",
        }

    async def _reflect_and_heal_node(self, state: WorkflowStateV2) -> dict[str, Any]:
        new_turn = state.get("turn", 1) + 1
        issues = state.get("validation_issues", [])
        error_context = f"Attempt {state.get('turn')} failed validation: {'; '.join(issues)}"
        logger.warning("[LangGraph V2] [NODE: reflect_and_heal] Turn %d/%d: %s", new_turn, state["max_turns"], error_context)

        schema = state["intent"]["schema_definition"]
        plan = await deep_agent_v2.autonomous_investigation(
            target_url=state["inspection_url"],
            target_schema=schema,
            failure_context=error_context,
        )
        return {
            "plan": plan.model_dump(),
            "turn": new_turn,
            "status": "TESTING",
        }

    async def _activate_endpoint_node(self, state: WorkflowStateV2) -> dict[str, Any]:
        logger.info("[LangGraph V2] [NODE: activate_endpoint] Promoting verified configuration to ACTIVE")
        intent = state["intent"]
        slug = intent["slug"]
        user_id = state.get("user_id", "default")
        plan_dict = state["plan"]
        dataset = state.get("extracted_data") or []

        endpoint_id = f"ep_v2_{hashlib.sha256((user_id + slug).encode()).hexdigest()[:12]}"
        api_key = f"mapik_{slug[:12]}_{secrets.token_hex(12)}"
        endpoint_path = f"/v2/api/{user_id}/{slug}"
        full_url = f"http://localhost:8001{endpoint_path}"
        curl_cmd = f"curl -H 'X-API-Key: {api_key}' '{full_url}'"

        inputs_dict = {
            k: {
                "type": v["type"],
                "description": v["description"],
                "default": v["default_value"],
            }
            for k, v in intent["inputs"].items()
        }

        await endpoint_repo_v2.save_endpoint(
            endpoint_id=endpoint_id,
            user_id=user_id,
            api_name=slug,
            slug=slug,
            target_url=state["target_url"],
            schema_definition=intent["schema_definition"],
            inputs=inputs_dict,
            plan=plan_dict,
            sample_data=dataset[:10],
            api_key=api_key,
        )

        response = {
            "endpoint_id": endpoint_id,
            "user_id": user_id,
            "api_name": slug,
            "slug": slug,
            "name": intent["name"],
            "status": "ACTIVE",
            "target_url": state["target_url"],
            "api_key": api_key,
            "endpoint_url": endpoint_path,
            "full_endpoint_url": full_url,
            "curl_command": curl_cmd,
            "api_specification": {
                "method": "GET",
                "path": endpoint_path,
                "inputs": inputs_dict,
                "outputs": intent["schema_definition"],
                "parameterized_url": state["target_url"],
            },
            "schema_definition": intent["schema_definition"],
            "sample_data": dataset[:5],
            "message": f"Endpoint '{endpoint_path}' is verified and active. You can query it dynamically.",
        }

        return {
            "status": "ACTIVE",
            "final_response": response,
        }

    async def _mark_failed_node(self, state: WorkflowStateV2) -> dict[str, Any]:
        issues = state.get("validation_issues", ["Unknown validation error"])
        logger.error("[LangGraph V2] [NODE: mark_failed] Workflow failed: %s", issues)
        return {
            "status": "FAILED",
            "error_message": f"Workflow failed verification after {state.get('turn')} turns: {'; '.join(issues)}",
        }


morphapi_workflow_v2 = MorphApiWorkflowV2()
