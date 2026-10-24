"""
Unit Tests for MorphAPI V2 Deep Agent Tools & Autonomous Decision Loop
"""

import pytest
from morphapi_v2.agent.tools import tool_registry_v2
from morphapi_v2.agent.deep_agent import deep_agent_v2
from morphapi_v2.agent.prompts import AGENT_SYSTEM_PROMPT_V2


def test_agent_tool_registry_definitions():
    tools = tool_registry_v2.get_tool_definitions()
    tool_names = [t["function"]["name"] for t in tools]
    assert "inspect_page" in tool_names
    assert "check_sniffed_network_api" in tool_names
    assert "analyze_dom_clusters" in tool_names
    assert "test_hierarchical_selectors" in tool_names
    assert "validate_sample_data" in tool_names
    assert "submit_extraction_plan" in tool_names


def test_system_prompt_contains_all_tools_and_strategy():
    assert "inspect_page" in AGENT_SYSTEM_PROMPT_V2
    assert "check_sniffed_network_api" in AGENT_SYSTEM_PROMPT_V2
    assert "analyze_dom_clusters" in AGENT_SYSTEM_PROMPT_V2
    assert "test_hierarchical_selectors" in AGENT_SYSTEM_PROMPT_V2
    assert "validate_sample_data" in AGENT_SYSTEM_PROMPT_V2
    assert "submit_extraction_plan" in AGENT_SYSTEM_PROMPT_V2
    assert "AGENT DECISION STRATEGY" in AGENT_SYSTEM_PROMPT_V2
    assert "TWO-TIER HIERARCHICAL" in AGENT_SYSTEM_PROMPT_V2


@pytest.mark.asyncio
async def test_agent_execute_validate_and_submit_tools():
    # 1. Test validate_sample_data tool
    sample_records = [
        {"title": "Project A", "link": "https://example.com/project/a"},
        {"title": "Project B", "link": "https://example.com/project/b"},
    ]
    val_res = await deep_agent_v2.execute_tool(
        "validate_sample_data",
        {"sample_records": sample_records, "schema_definition": {"title": "str", "link": "str"}},
    )
    assert val_res["is_valid"] is True
    assert val_res["checked_records"] == 2

    # 2. Test submit_extraction_plan tool
    submit_res = await deep_agent_v2.execute_tool(
        "submit_extraction_plan",
        {
            "strategy": "hierarchical_dom",
            "container_selector": "a.group",
            "field_rules": {
                "title": {"selector": "h3", "attribute": "text"},
                "link": {"selector": ".", "attribute": "href"},
            },
            "rationale": "Verified container selector matches open source cards",
        },
    )
    assert submit_res["accepted"] is True
    assert submit_res["plan"]["container_selector"] == "a.group"
    assert submit_res["plan"]["strategy"] == "hierarchical_dom"


@pytest.mark.asyncio
async def test_agent_tool_registry_disallows_prohibited_tools():
    res = await deep_agent_v2.execute_tool("raw_shell_exec", {"cmd": "ls"})
    assert "error" in res
    assert "disallowed" in res["error"] or "not registered" in res["error"]
