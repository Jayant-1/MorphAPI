"""
Unit Tests for Narrow Typed Agent Tools
Verifies tool execution, schema parameters, and strict absence of dangerous tools.
"""

import pytest
from morphapi.agent.tools import AgentToolRegistry
from morphapi.browser.playwright_manager import PlaywrightManager
from morphapi.schemas.errors import SsrfSecurityError


@pytest.mark.asyncio
async def test_tool_definitions_do_not_contain_dangerous_tools():
    registry = AgentToolRegistry()
    tool_defs = registry.get_tool_definitions()
    tool_names = [t["function"]["name"] for t in tool_defs]

    # Prohibited tools must NOT exist
    assert "run_shell" not in tool_names
    assert "execute_sql" not in tool_names
    assert "activate_endpoint" not in tool_names
    assert "write_database" not in tool_names
    assert "fetch_arbitrary_network" not in tool_names

    # Allowed tools MUST exist
    expected_tools = [
        "inspect_website",
        "inspect_element_context",
        "test_selectors",
        "extract_sample_data",
        "validate_extraction",
        "diagnose_extraction_failure",
        "request_customer_clarification",
        "submit_candidate_configuration",
        "get_endpoint_status",
    ]
    for expected in expected_tools:
        assert expected in tool_names, f"Tool '{expected}' should be registered"


@pytest.mark.asyncio
async def test_tool_inspect_website_ssrf_blocked(strict_url_policy):
    manager = PlaywrightManager(url_policy=strict_url_policy)
    registry = AgentToolRegistry(browser_manager=manager, url_policy=strict_url_policy)

    with pytest.raises(SsrfSecurityError):
        await registry.inspect_website("http://169.254.169.254/latest/meta-data")


@pytest.mark.asyncio
async def test_tool_submit_candidate_configuration_rejects_unsafe_selector():
    registry = AgentToolRegistry()
    result = await registry.submit_candidate_configuration(
        draft_id="d1",
        selector_map={"title": "javascript:alert(1)"},
        rationale="malicious injection",
        evidence_refs=[],
    )
    assert result["accepted"] is False
    assert "unsafe selector" in result["error"].lower()


@pytest.mark.asyncio
async def test_tool_submit_candidate_configuration_accepts_safe_candidate():
    registry = AgentToolRegistry()
    result = await registry.submit_candidate_configuration(
        draft_id="d1",
        selector_map={"title": "h1.product-title", "price": "div.price"},
        rationale="Clean selectors from live inspection",
        evidence_refs=["ev_123"],
    )
    assert result["accepted"] is True
    assert result["status"] == "SUBMITTED_FOR_VERIFICATION"
