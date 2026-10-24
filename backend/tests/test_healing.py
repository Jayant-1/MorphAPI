"""
Tests for LangGraph-powered Selector Discovery and Self-Healing Engine.
Tests bounded retries, live verification, atomic persistence, double-check locking, and failure isolation.
"""

import asyncio
from unittest.mock import AsyncMock
import pytest
from backend.app.adapters.nvidia_nim import NvidiaNimAdapter, CandidateSelectorsResponse
from backend.app.services.discovery_and_healing import DiscoveryAndHealingEngine
from backend.app.services.extraction import PlaywrightExtractionService


@pytest.mark.asyncio
async def test_successful_healing_with_live_verification(live_server_url):
    """
    Scenario: Website redesign mutates selectors.
    Old selectors fail -> NIM proposes valid new selectors ->
    Playwright validates candidate against live page -> Persist callback fired -> Success.
    """
    extraction_service = PlaywrightExtractionService(allow_local=True)
    target_url = f"{live_server_url}/mutated"
    schema = {"crop": "str", "price": "float"}
    failing_selectors = {"crop": ".mandi-crop", "price": ".rate-val"}

    # Mock NIM adapter to simulate DeepSeek proposal for mutated portal
    mock_nim = NvidiaNimAdapter(api_key="mock-key")
    mock_nim.propose_selectors = AsyncMock(
        return_value=CandidateSelectorsResponse(
            new_selectors={"crop": ".commodity-title", "price": ".market-price"},
            ai_reasoning="Discovered .commodity-title and .market-price in mutated grid layout",
            confidence_score=0.98,
        )
    )

    save_called = False
    saved_eid = None
    saved_selectors = None

    async def mock_save(eid, sels, rsn, ver):
        nonlocal save_called, saved_eid, saved_selectors
        save_called = True
        saved_eid = eid
        saved_selectors = sels

    engine = DiscoveryAndHealingEngine(
        extraction_service=extraction_service,
        nim_adapter=mock_nim,
    )

    result = await engine.heal_endpoint(
        endpoint_id="pune_mandi",
        target_url=target_url,
        schema_definition=schema,
        failing_selectors=failing_selectors,
        initial_failure_reason="Selectors matched 0 elements on mutated portal",
        save_callback=mock_save,
    )

    await extraction_service.close()

    assert result.success is True
    assert result.status == "SUCCESS"
    assert result.selectors == {"crop": ".commodity-title", "price": ".market-price"}
    assert save_called is True
    assert saved_eid == "pune_mandi"
    assert saved_selectors == {"crop": ".commodity-title", "price": ".market-price"}
    assert result.extraction_result.success is True
    assert len(result.extraction_result.data) == 3


@pytest.mark.asyncio
async def test_failed_healing_does_not_overwrite_selectors(live_server_url):
    """
    Scenario: Model proposes invalid selectors.
    Candidate fails live Playwright extraction -> Bounded retries exhausted ->
    Old selectors preserved -> Save callback is NEVER invoked -> Status is FAILED.
    """
    extraction_service = PlaywrightExtractionService(allow_local=True)
    target_url = f"{live_server_url}/mutated"
    schema = {"crop": "str", "price": "float"}
    failing_selectors = {"crop": ".mandi-crop", "price": ".rate-val"}

    # Mock NIM adapter returning bad selectors that still won't match
    mock_nim = NvidiaNimAdapter(api_key="mock-key")
    mock_nim.propose_selectors = AsyncMock(
        return_value=CandidateSelectorsResponse(
            new_selectors={"crop": ".still-not-found", "price": ".missing-price"},
            ai_reasoning="Faulty proposal",
            confidence_score=0.20,
        )
    )

    save_called = False

    async def mock_save(eid, sels, rsn, ver):
        nonlocal save_called
        save_called = True

    engine = DiscoveryAndHealingEngine(
        extraction_service=extraction_service,
        nim_adapter=mock_nim,
    )

    result = await engine.heal_endpoint(
        endpoint_id="pune_mandi",
        target_url=target_url,
        schema_definition=schema,
        failing_selectors=failing_selectors,
        initial_failure_reason="Original failure",
        save_callback=mock_save,
    )

    await extraction_service.close()

    assert result.success is False
    assert result.status == "FAILED"
    # Preserves original failing selectors
    assert result.selectors == failing_selectors
    # Must NOT have persisted unverified selectors
    assert save_called is False


@pytest.mark.asyncio
async def test_concurrent_healing_lock_and_double_check(live_server_url):
    """
    Scenario: Multiple simultaneous requests to a broken endpoint.
    Lock ensures only 1 healing cycle executes. The second request detects
    the healed selectors via double-check and does not repeat the healing cycle.
    """
    extraction_service = PlaywrightExtractionService(allow_local=True)
    target_url = f"{live_server_url}/mutated"
    schema = {"crop": "str", "price": "float"}
    failing_selectors = {"crop": ".mandi-crop", "price": ".rate-val"}

    stored_selectors = failing_selectors

    async def get_latest_selectors(eid: str):
        return stored_selectors

    async def mock_save(eid, sels, rsn, ver):
        nonlocal stored_selectors
        stored_selectors = sels

    mock_nim = NvidiaNimAdapter(api_key="mock-key")
    mock_nim.propose_selectors = AsyncMock(
        return_value=CandidateSelectorsResponse(
            new_selectors={"crop": ".commodity-title", "price": ".market-price"},
            ai_reasoning="Discovered selectors",
            confidence_score=0.95,
        )
    )

    engine = DiscoveryAndHealingEngine(
        extraction_service=extraction_service,
        nim_adapter=mock_nim,
    )

    # Launch two concurrent heal requests
    res1, res2 = await asyncio.gather(
        engine.heal_endpoint(
            endpoint_id="pune_mandi",
            target_url=target_url,
            schema_definition=schema,
            failing_selectors=failing_selectors,
            initial_failure_reason="Concurrent 1",
            get_latest_selectors_fn=get_latest_selectors,
            save_callback=mock_save,
        ),
        engine.heal_endpoint(
            endpoint_id="pune_mandi",
            target_url=target_url,
            schema_definition=schema,
            failing_selectors=failing_selectors,
            initial_failure_reason="Concurrent 2",
            get_latest_selectors_fn=get_latest_selectors,
            save_callback=mock_save,
        ),
    )

    await extraction_service.close()

    assert res1.success is True
    assert res2.success is True
    # NIM propose_selectors was called only once because the lock + double-check prevented duplicated healing
    assert mock_nim.propose_selectors.call_count == 1
