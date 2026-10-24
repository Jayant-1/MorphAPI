"""
Unit & Workflow Tests for MorphAPI V2 LangGraph StateGraph
"""

import pytest
from morphapi_v2.workflows.graph import morphapi_workflow_v2


def test_langgraph_graph_structure():
    graph = morphapi_workflow_v2.graph
    nodes = list(graph.nodes.keys())
    # Verify core LangGraph nodes exist
    assert "parse_intent" in nodes
    assert "inspect_and_sniff" in nodes
    assert "propose_plan" in nodes
    assert "test_extraction" in nodes
    assert "validate_results" in nodes
    assert "reflect_and_heal" in nodes
    assert "activate_endpoint" in nodes
    assert "mark_failed" in nodes


@pytest.mark.asyncio
async def test_langgraph_parse_intent_node():
    state = {
        "prompt": "Create an API for Y Combinator accepted companies from https://www.ycombinator.com/companies with configurable batch. Extract company name, description, and link.",
        "target_url": "https://www.ycombinator.com/companies?batch={batch}",
        "name": "yc-startups-v2",
        "user_id": "alice",
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

    res = await morphapi_workflow_v2._parse_intent_node(state)
    assert res["status"] == "INSPECTING"
    assert res["intent"]["slug"] == "yc-startups-v2"
    assert "company_name" in res["intent"]["schema_definition"]
    assert "description" in res["intent"]["schema_definition"]
    assert "link" in res["intent"]["schema_definition"]
    assert "batch" in res["intent"]["inputs"]


def test_langgraph_validation_decision():
    # 1. When data is verified, routes to activate_endpoint
    good_state = {
        "is_verified": True,
        "turn": 1,
        "max_turns": 3,
    }
    assert morphapi_workflow_v2.route_validation(good_state) == "activate_endpoint"

    # 2. When data is not verified and turn < max_turns, routes to reflect_and_heal
    healing_state = {
        "is_verified": False,
        "turn": 1,
        "max_turns": 3,
    }
    assert morphapi_workflow_v2.route_validation(healing_state) == "reflect_and_heal"

    # 3. When max turns exhausted, routes to mark_failed
    failed_state = {
        "is_verified": False,
        "turn": 3,
        "max_turns": 3,
    }
    assert morphapi_workflow_v2.route_validation(failed_state) == "mark_failed"
