"""
Unit & Integration Tests for NVIDIA NIM Provider Adapter
"""

import os
import pytest
from morphapi.agent.nim_provider import NvidiaNimProvider
from morphapi.schemas.errors import FailureCode, NIMProviderError


def test_nim_missing_api_key_raises_config_error():
    provider = NvidiaNimProvider(api_key="")
    with pytest.raises(NIMProviderError) as exc_info:
        provider.get_client()
    assert exc_info.value.code == FailureCode.NIM_CONFIG_ERROR


def test_nim_extract_json_from_markdown():
    provider = NvidiaNimProvider(api_key="test_key")
    raw_response = """
    Here are the candidate selectors:
    ```json
    {
        "new_selectors": {
            "title": "h1.product-title",
            "price": "span.price"
        },
        "ai_reasoning": "Located heading and price span in DOM",
        "confidence_score": 0.95
    }
    ```
    Please test them.
    """
    data = provider._extract_json(raw_response)
    assert "new_selectors" in data
    assert data["new_selectors"]["title"] == "h1.product-title"
    assert data["confidence_score"] == 0.95


def test_nim_extract_json_malformed_raises_error():
    provider = NvidiaNimProvider(api_key="test_key")
    with pytest.raises(NIMProviderError) as exc_info:
        provider._extract_json("Not a json at all {broken")
    assert exc_info.value.code == FailureCode.NIM_INFERENCE_ERROR


@pytest.mark.asyncio
async def test_live_nim_adapter_real_call():
    """
    Acceptance gate test against configured NVIDIA NIM endpoint.
    Only runs if NVIDIA_NIM_API_KEY is present; fails or skips with clear report.
    Never fakes success.
    """
    api_key = os.getenv("NVIDIA_NIM_API_KEY")
    if not api_key or not api_key.strip():
        pytest.skip("Acceptance test requires NVIDIA_NIM_API_KEY in environment.")

    provider = NvidiaNimProvider()
    schema = {"title": "str", "price": "float"}
    sample_dom = "<div class='product'><h2 class='name'>Apples</h2><p class='price'>$2.50</p></div>"

    patch = await provider.generate_selector_patch(
        schema_definition=schema,
        pruned_dom=sample_dom,
    )
    assert patch.new_selectors is not None
    assert "title" in patch.new_selectors
    assert "price" in patch.new_selectors
