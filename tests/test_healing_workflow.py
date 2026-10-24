"""
Acceptance Tests for LangGraph Durable Self-Healing Workflow
Verifies real browser candidate testing, deterministic backend validation gating,
and human approval rejection handling.
"""

from unittest.mock import AsyncMock, MagicMock
import pytest
from morphapi.browser.playwright_manager import PlaywrightManager
from morphapi.workflows.graph import MorphApiHealingGraph
from morphapi.agent.nim_provider import NvidiaNimProvider
from morphapi.schemas.contracts import SelectorPatch


@pytest.mark.asyncio
async def test_successful_healing_with_real_browser_verification(test_http_server, local_url_policy):
    target_url = f"{test_http_server}/product-redesign"
    schema = {"title": "str", "price": "float"}
    failing_selectors = {"title": "h1.old-title", "price": "div.old-price"}

    # Mock NIM model proposing the new selectors matching the redesigned HTML
    mock_nim = NvidiaNimProvider(api_key="mock_key")
    mock_nim.generate_selector_patch = AsyncMock(
        return_value=SelectorPatch(
            new_selectors={"title": "h2.item-heading", "price": "span.cost-badge"},
            ai_reasoning="Discovered updated heading and cost badge in redesigned markup",
            confidence_score=0.95,
        )
    )

    manager = PlaywrightManager(headless=True, url_policy=local_url_policy)
    promoted_record = {}

    async def mock_promote(endpoint_id, new_selectors, reasoning, version):
        promoted_record["endpoint_id"] = endpoint_id
        promoted_record["selectors"] = new_selectors
        promoted_record["version"] = version

    graph = MorphApiHealingGraph(
        browser_manager=manager,
        url_policy=local_url_policy,
        nim_provider=mock_nim,
        backend_promote_callback=mock_promote,
    )

    try:
        initial_state = {
            "endpoint_id": "test_heal_product",
            "workflow_id": "wf_test_001",
            "target_url": target_url,
            "schema_definition": schema,
            "active_selectors": failing_selectors,
            "version_promoted": 1,
            "error_context": "Previous selectors matched 0 elements",
        }

        config = {"configurable": {"thread_id": "thread_heal_001"}}
        final_state = await graph.graph.ainvoke(initial_state, config=config)

        assert final_state["is_verified"] is True
        assert final_state["status"] == "PROMOTED"
        assert final_state["version_promoted"] == 2
        assert final_state["active_selectors"]["title"] == "h2.item-heading"
        assert promoted_record.get("version") == 2
        assert promoted_record.get("selectors") == {"title": "h2.item-heading", "price": "span.cost-badge"}
    finally:
        await manager.close()


@pytest.mark.asyncio
async def test_failed_candidate_validation_does_not_promote(test_http_server, local_url_policy):
    target_url = f"{test_http_server}/product-redesign"
    schema = {"title": "str", "price": "float"}
    failing_selectors = {"title": "h1.old-title", "price": "div.old-price"}

    # Model proposes invalid selectors that match 0 elements
    mock_nim = NvidiaNimProvider(api_key="mock_key")
    mock_nim.generate_selector_patch = AsyncMock(
        return_value=SelectorPatch(
            new_selectors={"title": ".non-existent-header", "price": ".non-existent-price"},
            ai_reasoning="Hallucinated selectors",
            confidence_score=0.99,  # High model confidence must NOT bypass validation!
        )
    )

    manager = PlaywrightManager(headless=True, url_policy=local_url_policy)
    promote_called = False

    async def mock_promote(endpoint_id, new_selectors, reasoning, version):
        nonlocal promote_called
        promote_called = True

    graph = MorphApiHealingGraph(
        browser_manager=manager,
        url_policy=local_url_policy,
        nim_provider=mock_nim,
        backend_promote_callback=mock_promote,
    )

    try:
        initial_state = {
            "endpoint_id": "test_fail_product",
            "workflow_id": "wf_test_fail",
            "target_url": target_url,
            "schema_definition": schema,
            "active_selectors": failing_selectors,
            "max_attempts": 1,  # Stop after 1 attempt
            "version_promoted": 1,
            "error_context": "Initial failure",
        }

        config = {"configurable": {"thread_id": "thread_heal_fail"}}
        final_state = await graph.graph.ainvoke(initial_state, config=config)

        # Non-negotiable acceptance rule: model cannot self-certify; invalid candidates must NOT promote
        assert final_state["is_verified"] is False
        assert final_state["status"] == "FAILED"
        assert promote_called is False
    finally:
        await manager.close()


@pytest.mark.asyncio
async def test_approval_rejection_marks_failed(test_http_server, local_url_policy):
    target_url = f"{test_http_server}/product-redesign"
    schema = {"title": "str", "price": "float"}

    # Model proposes valid selectors, but approval is rejected by operator
    mock_nim = NvidiaNimProvider(api_key="mock_key")
    mock_nim.generate_selector_patch = AsyncMock(
        return_value=SelectorPatch(
            new_selectors={"title": "h2.item-heading", "price": "span.cost-badge"},
            ai_reasoning="Discovered selectors",
            confidence_score=0.9,
        )
    )

    manager = PlaywrightManager(headless=True, url_policy=local_url_policy)
    promote_called = False

    async def mock_promote(*args):
        nonlocal promote_called
        promote_called = True

    graph = MorphApiHealingGraph(
        browser_manager=manager,
        url_policy=local_url_policy,
        nim_provider=mock_nim,
        backend_promote_callback=mock_promote,
    )

    try:
        initial_state = {
            "endpoint_id": "test_approval_reject",
            "workflow_id": "wf_approval",
            "target_url": target_url,
            "schema_definition": schema,
            "active_selectors": {},
            "requires_approval": True,
            "approval_granted": False,  # Rejected by human operator
            "version_promoted": 1,
        }

        config = {"configurable": {"thread_id": "thread_approval"}}
        final_state = await graph.graph.ainvoke(initial_state, config=config)

        assert final_state["status"] == "FAILED"
        assert promote_called is False
    finally:
        await manager.close()
