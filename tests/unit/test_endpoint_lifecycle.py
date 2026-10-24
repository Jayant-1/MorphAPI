"""
Unit Tests for MorphAPI Endpoint Lifecycle & Atomic Versioning
Covers draft creation, candidate isolation, deterministic verification,
atomic backend-controlled promotion, and rollback to last-known-good.
"""

import os
import pytest
import pytest_asyncio
from morphapi.db.migrations import run_migrations
from morphapi.db.repository import CandidateNotVerifiedError, EndpointRepository, VersionRepository
from morphapi.schemas.audit import AuditEventType
from morphapi.schemas.endpoint import (
    CandidateSubmitRequest,
    CandidateVerifyRequest,
    EndpointCreateRequest,
    EndpointStatus,
    VersionStatus,
)
from morphapi.services.endpoint_service import EndpointService


@pytest_asyncio.fixture
async def temp_endpoint_service(tmp_path):
    db_file = str(tmp_path / "lifecycle_test.db")
    await run_migrations(db_path=db_file)
    ep_repo = EndpointRepository(db_path=db_file)
    ver_repo = VersionRepository(db_path=db_file)
    service = EndpointService(endpoint_repo=ep_repo, version_repo=ver_repo)
    return service, ep_repo, ver_repo


@pytest.mark.asyncio
async def test_create_endpoint_draft_initial_state(temp_endpoint_service):
    service, ep_repo, ver_repo = temp_endpoint_service

    req = EndpointCreateRequest(
        name="Test Ecommerce API",
        slug="test-ecom",
        target_url="https://example.com/products",
        schema_definition={"title": "str", "price": "float"},
    )

    created = await service.create_endpoint_draft(req)
    assert created.endpoint_id.startswith("ep_")
    assert created.slug == "test-ecom"
    assert created.status == EndpointStatus.DRAFT
    assert created.active_version_id is None
    assert created.last_known_good_version_id is None

    # Version 1 is created in DRAFT status
    versions = await service.list_versions(created.endpoint_id)
    assert len(versions) == 1
    assert versions[0].version_number == 1
    assert versions[0].status == VersionStatus.DRAFT
    assert versions[0].is_active is False


@pytest.mark.asyncio
async def test_submit_candidate_version_isolation(temp_endpoint_service):
    service, ep_repo, ver_repo = temp_endpoint_service

    req = EndpointCreateRequest(
        name="Crypto Rates API",
        target_url="https://example.com/crypto",
        schema_definition={"asset": "str", "rate": "float"},
    )
    ep = await service.create_endpoint_draft(req)

    # Agent submits candidate selectors
    candidate_req = CandidateSubmitRequest(
        selector_map={"asset": "h1.asset-name", "rate": "span.price"},
        rationale="Agent proposed CSS selectors based on semantic DOM structure",
    )
    candidate_ver = await service.submit_candidate(ep.endpoint_id, candidate_req, created_by="deepagents")

    assert candidate_ver.version_id.startswith("ver_")
    assert candidate_ver.version_number == 2
    assert candidate_ver.status == VersionStatus.CANDIDATE
    assert candidate_ver.is_active is False
    assert candidate_ver.selector_map["asset"] == "h1.asset-name"

    # Crucial Rule: Candidate is stored, but NOT active and NOT verified!
    refreshed_ep = await service.get_endpoint(ep.endpoint_id)
    assert refreshed_ep.active_version_id is None
    assert refreshed_ep.status == EndpointStatus.DRAFT


@pytest.mark.asyncio
async def test_cannot_activate_unverified_candidate(temp_endpoint_service):
    service, ep_repo, ver_repo = temp_endpoint_service

    req = EndpointCreateRequest(
        name="Stock API",
        target_url="https://example.com/stocks",
        schema_definition={"ticker": "str", "price": "float"},
    )
    ep = await service.create_endpoint_draft(req)

    cand_req = CandidateSubmitRequest(
        selector_map={"ticker": "span.symbol", "price": "span.price"}
    )
    cand_ver = await service.submit_candidate(ep.endpoint_id, cand_req)

    # Attempting to activate an unverified candidate must fail!
    with pytest.raises(CandidateNotVerifiedError) as exc_info:
        await service.activate_version(ep.endpoint_id, cand_ver.version_id)

    assert "Cannot activate version" in str(exc_info.value)
    assert "CANDIDATE" in str(exc_info.value)


@pytest.mark.asyncio
async def test_deterministic_verification_and_atomic_promotion(temp_endpoint_service):
    service, ep_repo, ver_repo = temp_endpoint_service

    req = EndpointCreateRequest(
        name="Weather API",
        target_url="https://example.com/weather",
        schema_definition={"city": "str", "temp": "float", "is_sunny": "bool"},
    )
    ep = await service.create_endpoint_draft(req)

    cand_req = CandidateSubmitRequest(
        selector_map={"city": "div.city", "temp": "div.temp", "is_sunny": "div.condition"}
    )
    cand_ver = await service.submit_candidate(ep.endpoint_id, cand_req)

    # 1. Run deterministic verification with valid sample data
    valid_sample = {"city": "San Francisco", "temp": "68.5", "is_sunny": "true"}
    verify_resp = await service.verify_candidate(
        ep.endpoint_id,
        cand_ver.version_id,
        request=CandidateVerifyRequest(sample_data=valid_sample),
    )
    assert verify_resp.verified is True
    assert verify_resp.status == VersionStatus.VERIFIED
    assert verify_resp.sample_data["temp"] == 68.5
    assert verify_resp.sample_data["is_sunny"] is True

    # 2. Promote verified version to ACTIVE atomically
    promoted_ep, promoted_ver = await service.activate_version(ep.endpoint_id, cand_ver.version_id)
    assert promoted_ep.status == EndpointStatus.ACTIVE
    assert promoted_ep.active_version_id == cand_ver.version_id
    assert promoted_ver.is_active is True
    assert promoted_ver.status == VersionStatus.ACTIVE
    assert promoted_ver.activated_at is not None


@pytest.mark.asyncio
async def test_atomic_version_evolution_and_rollback(temp_endpoint_service):
    service, ep_repo, ver_repo = temp_endpoint_service

    req = EndpointCreateRequest(
        name="News API",
        target_url="https://example.com/news",
        schema_definition={"headline": "str"},
    )
    ep = await service.create_endpoint_draft(req)

    # Version 2: First good version
    cand2 = await service.submit_candidate(ep.endpoint_id, CandidateSubmitRequest(selector_map={"headline": "h1.title"}))
    await service.verify_candidate(ep.endpoint_id, cand2.version_id, CandidateVerifyRequest(sample_data={"headline": "Breaking News"}))
    ep_v2, ver_v2 = await service.activate_version(ep.endpoint_id, cand2.version_id)
    assert ep_v2.active_version_id == cand2.version_id

    # Version 3: Second good version (site update)
    cand3 = await service.submit_candidate(ep.endpoint_id, CandidateSubmitRequest(selector_map={"headline": "h2.main-headline"}))
    await service.verify_candidate(ep.endpoint_id, cand3.version_id, CandidateVerifyRequest(sample_data={"headline": "Latest Update"}))
    ep_v3, ver_v3 = await service.activate_version(ep.endpoint_id, cand3.version_id)

    assert ep_v3.active_version_id == cand3.version_id
    assert ep_v3.last_known_good_version_id == cand2.version_id

    # Verify version 2 was marked as last-known-good and retired
    v2_record = await service.get_version(ep.endpoint_id, cand2.version_id)
    assert v2_record.is_active is False
    assert v2_record.is_last_known_good is True
    assert v2_record.status == VersionStatus.RETIRED

    # Rollback to last known good (cand2)
    rolled_ep, restored_ver = await service.rollback(ep.endpoint_id, reason="Version 3 introduced unwanted artifacts")
    assert rolled_ep.active_version_id == cand2.version_id
    assert restored_ver.version_id == cand2.version_id
    assert restored_ver.is_active is True
