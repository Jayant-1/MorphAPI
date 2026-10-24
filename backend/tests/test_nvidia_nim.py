"""
Tests for NVIDIA NIM Adapter.
Includes unit tests with strict Pydantic parsing and live verification against real NIM if credentials configured.
"""

import os
import pytest
from backend.app.adapters.nvidia_nim import (
    NvidiaNimAdapter,
    CandidateSelectorsResponse,
    NIMConfigurationError,
    NIMInferenceError,
)


def test_candidate_selectors_response_validation():
    # Valid candidate response
    valid_data = {
        "new_selectors": {"crop": ".mandi-crop", "price": ".rate-val"},
        "ai_reasoning": "Located crop names in .mandi-crop and price values in .rate-val",
        "confidence_score": 0.95,
    }
    model = CandidateSelectorsResponse(**valid_data)
    assert model.new_selectors["crop"] == ".mandi-crop"
    assert model.confidence_score == 0.95


def test_candidate_selectors_rejects_empty():
    with pytest.raises(ValueError):
        CandidateSelectorsResponse(new_selectors={}, ai_reasoning="None")

    with pytest.raises(ValueError):
        CandidateSelectorsResponse(
            new_selectors={"crop": ""},
            ai_reasoning="Empty selector",
        )


def test_candidate_selectors_rejects_malicious_selector():
    with pytest.raises(ValueError) as exc:
        CandidateSelectorsResponse(
            new_selectors={"crop": "javascript:alert(1)"},
            ai_reasoning="Malicious payload",
        )
    assert "Unsafe selector" in str(exc.value)


def test_nim_adapter_missing_api_key_raises_config_error():
    adapter = NvidiaNimAdapter(api_key="")
    with pytest.raises(NIMConfigurationError):
        adapter._get_client()


def test_nim_extract_json_from_markdown():
    adapter = NvidiaNimAdapter(api_key="test-key")
    raw = """Here is the mapping:
```json
{
  "new_selectors": {"crop": ".crop-col", "price": ".price-col"},
  "ai_reasoning": "Detected from table header"
}
```
Hope this helps!"""
    data = adapter._extract_json(raw)
    assert data["new_selectors"]["crop"] == ".crop-col"


def test_nim_extract_json_malformed_raises_inference_error():
    adapter = NvidiaNimAdapter(api_key="test-key")
    raw = "Not a json response at all"
    with pytest.raises(NIMInferenceError):
        adapter._extract_json(raw)


@pytest.mark.asyncio
async def test_live_nim_adapter_real_call():
    """
    Live test against configured NVIDIA NIM deployment.
    If NVIDIA_NIM_API_KEY is not configured, marked BLOCKED (never simulated).
    """
    api_key = os.getenv("NVIDIA_NIM_API_KEY")
    if not api_key or not api_key.strip():
        pytest.skip("BLOCKED: NVIDIA_NIM_API_KEY is not configured in environment. Simulation is forbidden.")

    adapter = NvidiaNimAdapter()
    schema = {"title": "str"}
    html_sample = "<html><body><h1 id='main-title'>Welcome to MorphAPI</h1></body></html>"

    response = await adapter.propose_selectors(
        target_url="https://example.com",
        page_title="Example",
        schema_definition=schema,
        pruned_dom=html_sample,
    )

    assert "title" in response.new_selectors
    assert response.new_selectors["title"] != ""
