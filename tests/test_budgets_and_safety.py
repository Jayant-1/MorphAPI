"""
Tests for Budget Guardrails, Timeouts, and Fast Path Bypass
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock
import pytest

from morphapi.workflows.policies import is_budget_exhausted
from morphapi.agent.builder_agent import DeepAgentsHarness
from morphapi.agent.nim_provider import NvidiaNimProvider
from morphapi.agent.tools import AgentToolRegistry
from morphapi.services.extraction_service import SharedExtractionService
from morphapi.browser.playwright_manager import PlaywrightManager
from morphapi.browser.extractor import BrowserExtractor
from morphapi.services.validation_service import ValidationService


def test_is_budget_exhausted_attempt_limit():
    state = {"attempt_count": 3, "max_attempts": 3}
    exhausted, reason = is_budget_exhausted(state)
    assert exhausted is True
    assert "Maximum attempt budget exhausted" in reason


def test_is_budget_exhausted_tool_call_limit():
    state = {"tool_call_count": 10, "max_tool_calls": 10, "attempt_count": 1, "max_attempts": 3}
    exhausted, reason = is_budget_exhausted(state)
    assert exhausted is True
    assert "Tool-call budget exhausted" in reason


def test_is_budget_exhausted_wall_clock_deadline():
    # Deadline in the past
    state = {
        "deadline_ts": time.monotonic() - 5.0,
        "attempt_count": 1,
        "max_attempts": 3,
        "tool_call_count": 2,
        "max_tool_calls": 10,
    }
    exhausted, reason = is_budget_exhausted(state)
    assert exhausted is True
    assert "deadline exceeded" in reason.lower()


@pytest.mark.asyncio
async def test_deepagents_harness_enforces_tool_call_budget():
    provider = NvidiaNimProvider(api_key="mock_key")

    # Mock completion repeatedly calling a tool without submitting
    round_msg = MagicMock()
    round_msg.content = None
    tc = MagicMock()
    tc.id = "tc_loop"
    tc.function.name = "get_endpoint_status"
    tc.function.arguments = '{"endpoint_id": "test_ep"}'
    round_msg.tool_calls = [tc]
    resp = MagicMock(choices=[MagicMock(message=round_msg)])

    provider.create_chat_completion = AsyncMock(return_value=resp)
    registry = AgentToolRegistry()

    # Budget of only 2 tool calls
    harness = DeepAgentsHarness(
        provider=provider,
        tool_registry=registry,
        max_tool_calls=2,
    )

    result = await harness.investigate_and_propose(
        target_url="https://example.com",
        schema_definition={"title": "str"},
    )

    assert result.success is False
    assert result.tool_calls_executed == 2
    assert "Tool call budget exhausted" in result.error_message


@pytest.mark.asyncio
async def test_fast_path_bypasses_model_and_workflow_on_success(test_http_server, local_url_policy):
    target_url = f"{test_http_server}/product"
    manager = PlaywrightManager(headless=True, url_policy=local_url_policy)
    extractor = BrowserExtractor(manager=manager)
    validator = ValidationService()

    # Mock healing service to verify it is NEVER called on successful fast path
    mock_healer = MagicMock()
    mock_healer.heal_endpoint = AsyncMock()

    service = SharedExtractionService(
        extractor=extractor,
        validator=validator,
        healing_service=mock_healer,
    )

    schema = {"title": "str", "price": "float"}
    valid_selectors = {"title": "h1.product-title", "price": "div.product-price"}

    try:
        response = await service.extract(
            endpoint_id="fast_product",
            target_url=target_url,
            schema_definition=schema,
            selectors=valid_selectors,
            auto_heal=True,
        )

        assert response.execution_path == "FAST_PATH"
        assert response.healed_this_request is False
        assert response.data["title"] == "Organic Fuji Apples"
        assert response.data["price"] == 4.99

        # Healing service (and LLM) was completely bypassed!
        assert mock_healer.heal_endpoint.call_count == 0
    finally:
        await manager.close()
