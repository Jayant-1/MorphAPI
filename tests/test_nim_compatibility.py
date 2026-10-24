"""
Unit & Acceptance Tests for NVIDIA NIM Tool-Calling Compatibility Preflight
"""

from unittest.mock import AsyncMock, MagicMock
import pytest
from morphapi.agent.compatibility import NIMCompatibilityPreflight, NIMPreflightResult
from morphapi.agent.nim_provider import NvidiaNimProvider
from morphapi.schemas.errors import FailureCode, NIMProviderError


@pytest.mark.asyncio
async def test_preflight_success_round_trip():
    provider = NvidiaNimProvider(api_key="mock_key")

    # Round 1 response: Model issues tool call
    round1_msg = MagicMock()
    round1_msg.content = None
    tc = MagicMock()
    tc.id = "call_123"
    tc.function.name = "verify_ping"
    tc.function.arguments = '{"challenge_token": "morphapi_preflight_9981"}'
    round1_msg.tool_calls = [tc]
    resp1 = MagicMock()
    resp1.choices = [MagicMock(message=round1_msg)]

    # Round 2 response: Model returns follow-up text
    round2_msg = MagicMock()
    round2_msg.content = "Connectivity verified successfully."
    resp2 = MagicMock()
    resp2.choices = [MagicMock(message=round2_msg)]

    provider.create_chat_completion = AsyncMock(side_effect=[resp1, resp2])

    preflight = NIMCompatibilityPreflight(provider=provider)
    result: NIMPreflightResult = await preflight.run_preflight()

    assert result.ready is True
    assert result.tool_calling_supported is True
    assert result.round_trip_success is True
    assert result.error_message is None
    assert provider.create_chat_completion.call_count == 2


@pytest.mark.asyncio
async def test_preflight_fails_when_model_does_not_call_tool():
    provider = NvidiaNimProvider(api_key="mock_key")

    # Model returns text without tool_calls
    msg = MagicMock()
    msg.content = "I do not support tools."
    msg.tool_calls = None
    resp = MagicMock()
    resp.choices = [MagicMock(message=msg)]

    provider.create_chat_completion = AsyncMock(return_value=resp)

    preflight = NIMCompatibilityPreflight(provider=provider)
    result: NIMPreflightResult = await preflight.run_preflight()

    assert result.ready is False
    assert result.tool_calling_supported is False
    assert "did not return any tool_calls" in result.error_message


@pytest.mark.asyncio
async def test_preflight_fails_on_malformed_arguments():
    provider = NvidiaNimProvider(api_key="mock_key")

    msg = MagicMock()
    msg.content = None
    tc = MagicMock()
    tc.id = "call_456"
    tc.function.name = "verify_ping"
    tc.function.arguments = "malformed_json_not_an_object"
    msg.tool_calls = [tc]
    resp = MagicMock()
    resp.choices = [MagicMock(message=msg)]

    provider.create_chat_completion = AsyncMock(return_value=resp)

    preflight = NIMCompatibilityPreflight(provider=provider)
    result = await preflight.run_preflight()

    assert result.ready is False
    assert "malformed JSON arguments" in result.error_message


@pytest.mark.asyncio
async def test_preflight_fails_on_provider_error():
    provider = NvidiaNimProvider(api_key="mock_key")
    provider.create_chat_completion = AsyncMock(
        side_effect=NIMProviderError(FailureCode.NIM_RATE_LIMITED, "Rate limited")
    )

    preflight = NIMCompatibilityPreflight(provider=provider)
    result = await preflight.run_preflight()

    assert result.ready is False
    assert "Rate limited" in result.error_message
    assert result.diagnostic_details.get("failure_code") == FailureCode.NIM_RATE_LIMITED.value
