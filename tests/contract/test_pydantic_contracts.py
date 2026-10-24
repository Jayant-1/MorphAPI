"""
Contract Tests for MorphAPI Pydantic v2 Shared Schemas
Ensures serialization, field constraints, rejection of invalid data,
and parity across Person 1, Person 2, and Person 3 boundaries.
"""

import pytest
from pydantic import ValidationError
from morphapi.schemas.audit import AuditEvent, AuditEventType
from morphapi.schemas.contracts import (
    EndpointRegisterRequest,
    ExecutionPath,
    ExtractionResponse,
    FieldEvidence,
    SelectorPatch,
    ValidationResult,
)
from morphapi.schemas.endpoint import (
    CandidateSubmitRequest,
    EndpointCreateRequest,
    EndpointStatus,
    VersionStatus,
)
from morphapi.schemas.errors import ErrorResponse, FailureCode


def test_endpoint_create_request_contract():
    req = EndpointCreateRequest(
        name="Test API",
        slug="test-slug",
        target_url="https://example.com",
        schema_definition={"title": "str", "price": "float"},
        allowed_url_scope=["https://example.com/items/*"],
        freshness_seconds=600,
    )
    dumped = req.model_dump()
    assert dumped["name"] == "Test API"
    assert dumped["freshness_seconds"] == 600

    # Invalid URL scheme must raise ValidationError
    with pytest.raises(ValidationError):
        EndpointCreateRequest(
            name="Invalid Scheme",
            target_url="ftp://invalid.com",
            schema_definition={"title": "str"},
        )


def test_selector_patch_rejects_empty():
    with pytest.raises(ValueError):
        SelectorPatch(
            new_selectors={},
            ai_reasoning="empty",
        )

    with pytest.raises(ValueError):
        SelectorPatch(
            new_selectors={"title": "   "},
            ai_reasoning="empty selector value",
        )


def test_candidate_submit_request_validation():
    req = CandidateSubmitRequest(
        selector_map={"title": "h1.title", "price": "span.price"},
        rationale="CSS selector mapping",
        evidence_refs=["dom_snapshot_1"],
    )
    assert req.selector_map["title"] == "h1.title"

    with pytest.raises(ValueError):
        CandidateSubmitRequest(selector_map={})


def test_error_response_contract():
    err = ErrorResponse(
        error_code=FailureCode.SSRF_DETECTED,
        message="Destination IP blocked",
        endpoint_id="ep_123",
        retryable=False,
        details={"ip": "169.254.169.254"},
    )
    dumped = err.model_dump()
    assert dumped["error_code"] == "SSRF_DETECTED"
    assert dumped["retryable"] is False


def test_audit_event_contract():
    event = AuditEvent(
        correlation_id="corr_abc",
        tenant_id="tenant_1",
        actor="backend_worker",
        action=AuditEventType.VERSION_ACTIVATED,
        target_type="endpoint",
        target_id="ep_xyz",
        details={"version": 2},
    )
    dumped = event.model_dump()
    assert dumped["action"] == "VERSION_ACTIVATED"
    assert dumped["correlation_id"] == "corr_abc"
