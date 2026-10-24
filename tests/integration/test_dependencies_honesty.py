"""
MorphAPI Honest Integration Tests
Tests live dependencies to verify they fail honestly without simulated fake responses
when real external or browser dependencies fail.
"""

import os
import pytest
from morphapi.browser.extractor import BrowserExtractor
from morphapi.browser.playwright_manager import PlaywrightManager
from morphapi.browser.url_policy import UrlPolicyService
from morphapi.schemas.endpoint import CandidateSubmitRequest, CandidateVerifyRequest
from morphapi.schemas.errors import FailureCode, MorphApiError
from morphapi.services.endpoint_service import EndpointService
from morphapi.services.validation_service import ValidationService


@pytest.mark.asyncio
async def test_unreachable_target_fails_honestly_without_fake_success():
    """
    Verifies that calling browser extraction on an unreachable destination fails honestly
    with a real error instead of returning a simulated empty/success payload.
    """
    # Use an RFC5737 test IP on a closed port
    unreachable_url = "http://192.0.2.1:54321/api"
    url_policy = UrlPolicyService(allow_local=True)
    manager = PlaywrightManager(headless=True, url_policy=url_policy, navigation_timeout_ms=3000)
    extractor = BrowserExtractor(manager=manager)

    try:
        result = await extractor.extract(
            endpoint_id="test_unreachable",
            target_url=unreachable_url,
            schema_definition={"title": "str"},
            selector_map={"title": "h1"},
        )

        # Must fail honestly! Never return fake success!
        assert result.success is False
        assert result.data is None
        assert result.error_code in (
            FailureCode.BROWSER_RESOURCE_ERROR,
            FailureCode.BROWSER_TIMEOUT,
            FailureCode.BROWSER_NAVIGATION_ERROR,
        )
    finally:
        await manager.close()


@pytest.mark.asyncio
async def test_broken_selectors_fail_verification_honestly(test_http_server, local_url_policy):
    """
    Verifies that testing broken selectors on a live rendered page fails honestly,
    recording 0 matches and refusing to verify or promote the candidate.
    """
    manager = PlaywrightManager(headless=True, url_policy=local_url_policy)
    extractor = BrowserExtractor(manager=manager)
    validator = ValidationService()
    service = EndpointService(browser_extractor=extractor, validation_service=validator)

    target_url = f"{test_http_server}/product"
    schema = {"title": "str", "price": "float"}
    broken_selectors = {"title": "h1.nonexistent-class", "price": "div.missing-price"}

    try:
        from morphapi.schemas.endpoint import EndpointCreateRequest
        ep = await service.create_endpoint_draft(
            EndpointCreateRequest(
                name="Honest Fail Test",
                target_url=target_url,
                schema_definition=schema,
            )
        )

        cand = await service.submit_candidate(
            ep.endpoint_id,
            CandidateSubmitRequest(selector_map=broken_selectors, rationale="Broken test selectors"),
        )

        # Run live browser verification
        verify_res = await service.verify_candidate(ep.endpoint_id, cand.version_id)

        # Must fail honestly: matched_count == 0, verified == False
        assert verify_res.verified is False
        assert verify_res.selector_test_passed is False
        assert any("0 elements matched" in issue or "failed" in issue for issue in verify_res.issues)

        # Candidate must remain in REJECTED status
        ver_record = await service.get_version(ep.endpoint_id, cand.version_id)
        assert ver_record.status.value == "REJECTED"
        assert ver_record.is_active is False
    finally:
        await manager.close()


@pytest.mark.asyncio
async def test_nim_fails_honestly_when_unconfigured():
    """
    Verifies that the NVIDIA NIM provider raises an explicit NIMProviderError
    when credentials are missing, rather than fabricating a fake LLM response.
    """
    from morphapi.agent.nim_provider import NvidiaNimProvider

    # Clear env key
    provider = NvidiaNimProvider(api_key="")
    with pytest.raises(MorphApiError) as exc_info:
        await provider.create_chat_completion(messages=[{"role": "user", "content": "hello"}])

    assert exc_info.value.code == FailureCode.NIM_CONFIG_ERROR
    assert "missing" in exc_info.value.message.lower() or "api key" in exc_info.value.message.lower()
