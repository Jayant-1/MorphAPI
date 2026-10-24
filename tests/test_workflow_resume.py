"""
Tests for Workflow State Checkpointing, Resume, and Idempotent Side Effects
"""

from unittest.mock import AsyncMock
import pytest
from morphapi.browser.playwright_manager import PlaywrightManager
from morphapi.workflows.graph import MorphApiHealingGraph
from morphapi.workflows.checkpointer import WorkflowCheckpointer
from morphapi.agent.nim_provider import NvidiaNimProvider
from morphapi.schemas.contracts import SelectorPatch


@pytest.mark.asyncio
async def test_idempotent_resume_prevents_duplicate_promotion(test_http_server, local_url_policy):
    target_url = f"{test_http_server}/product-redesign"
    schema = {"title": "str", "price": "float"}

    mock_nim = NvidiaNimProvider(api_key="mock_key")
    mock_nim.generate_selector_patch = AsyncMock(
        return_value=SelectorPatch(
            new_selectors={"title": "h2.item-heading", "price": "span.cost-badge"},
            ai_reasoning="Discovered selectors",
            confidence_score=0.9,
        )
    )

    checkpointer = WorkflowCheckpointer()
    manager = PlaywrightManager(headless=True, url_policy=local_url_policy)
    promote_count = 0

    async def mock_promote(endpoint_id, new_selectors, reasoning, version):
        nonlocal promote_count
        promote_count += 1

    graph = MorphApiHealingGraph(
        browser_manager=manager,
        url_policy=local_url_policy,
        nim_provider=mock_nim,
        checkpointer=checkpointer,
        backend_promote_callback=mock_promote,
    )

    try:
        workflow_id = "wf_idempotent_test"
        thread_id = "thread_idempotent_1"
        config = {"configurable": {"thread_id": thread_id}}

        initial_state = {
            "endpoint_id": "test_idempotent",
            "workflow_id": workflow_id,
            "target_url": target_url,
            "schema_definition": schema,
            "active_selectors": {},
            "version_promoted": 1,
        }

        # First run: executes promotion
        state1 = await graph.graph.ainvoke(initial_state, config=config)
        assert state1["status"] == "PROMOTED"
        assert promote_count == 1

        # Second run / resume with same workflow_id and next version:
        # Checkpointer idempotency guard must prevent duplicate callback execution!
        state2 = await graph.graph.ainvoke(state1, config=config)
        assert state2["status"] == "PROMOTED"
        assert promote_count == 1  # Still exactly 1! Duplicate prevented.
    finally:
        await manager.close()


def test_checkpointer_marks_and_detects_executed_side_effects():
    checkpointer = WorkflowCheckpointer()
    workflow_id = "job_456"
    version = 2

    # First attempt: safe to execute
    first_attempt = checkpointer.mark_promotion_executed(workflow_id, version)
    assert first_attempt is True
    assert checkpointer.is_promotion_executed(workflow_id, version) is True

    # Duplicate attempt on resume: prevented
    second_attempt = checkpointer.mark_promotion_executed(workflow_id, version)
    assert second_attempt is False
