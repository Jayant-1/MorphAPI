"""
MorphAPI Endpoint Lifecycle Contracts
Defines endpoint drafts, versions, candidate submission, verification, activation, and rollback.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field, HttpUrl, field_validator


class EndpointStatus(str, Enum):
    DRAFT = "DRAFT"
    INSPECTING = "INSPECTING"
    CANDIDATE_READY = "CANDIDATE_READY"
    VERIFIED = "VERIFIED"
    ACTIVE = "ACTIVE"
    DEGRADED = "DEGRADED"
    HEALING = "HEALING"
    NEEDS_APPROVAL = "NEEDS_APPROVAL"
    RETIRED = "RETIRED"


class VersionStatus(str, Enum):
    DRAFT = "DRAFT"
    CANDIDATE = "CANDIDATE"
    VERIFIED = "VERIFIED"
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"
    REJECTED = "REJECTED"


class EndpointCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Display name for the endpoint")
    slug: str | None = Field(default=None, pattern=r"^[a-zA-Z0-9_-]{2,80}$", description="Optional unique slug / endpoint_id")
    target_url: HttpUrl = Field(..., description="Target website URL")
    schema_definition: dict[str, str] = Field(..., min_length=1, description="Field name to type mapping (e.g. {'title': 'str', 'price': 'float'})")
    allowed_url_scope: list[str] = Field(default_factory=list, description="List of URL patterns/domains allowed for navigation")
    initial_selectors: dict[str, str] | None = Field(default=None, description="Optional starting selectors if known")
    field_descriptions: dict[str, str] = Field(default_factory=dict, description="Optional descriptions for LLM context")
    extraction_hints: dict[str, Any] = Field(default_factory=dict, description="Optional hints, e.g. pagination or wait selectors")
    freshness_seconds: int = Field(default=300, ge=0, description="Cache freshness expectation in seconds")


class EndpointResponse(BaseModel):
    endpoint_id: str
    tenant_id: str
    name: str
    slug: str
    target_url: str
    allowed_url_scope: list[str]
    status: EndpointStatus
    active_version_id: str | None = None
    last_known_good_version_id: str | None = None
    schema_definition: dict[str, str]
    created_at: str
    updated_at: str


class EndpointVersionResponse(BaseModel):
    version_id: str
    endpoint_id: str
    version_number: int
    schema_definition: dict[str, str]
    selector_map: dict[str, str]
    status: VersionStatus
    is_active: bool
    is_last_known_good: bool
    verification_result: dict[str, Any] | None = None
    rationale: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    created_by: str = "user"
    verified_at: str | None = None
    activated_at: str | None = None
    created_at: str


class CandidateSubmitRequest(BaseModel):
    selector_map: dict[str, str] = Field(..., min_length=1, description="Proposed field selectors")
    rationale: str = Field(default="Proposed candidate selector configuration", description="Reasoning or description")
    evidence_refs: list[str] = Field(default_factory=list, description="References to DOM snapshots or context")

    @field_validator("selector_map")
    @classmethod
    def validate_selectors_not_empty(cls, v: dict[str, str]) -> dict[str, str]:
        for k, sel in v.items():
            if not sel or not isinstance(sel, str) or not sel.strip():
                raise ValueError(f"Selector for field '{k}' cannot be empty")
        return v


class CandidateVerifyRequest(BaseModel):
    test_url: str | None = Field(default=None, description="Optional override test URL")
    sample_data: dict[str, Any] | None = Field(default=None, description="Optional offline sample data for pure deterministic test")


class CandidateVerifyResponse(BaseModel):
    verified: bool
    status: VersionStatus
    validation_passed: bool
    selector_test_passed: bool
    issues: list[str] = Field(default_factory=list)
    selector_match_counts: dict[str, int] = Field(default_factory=dict)
    sample_data: Any = None


class EndpointActivateRequest(BaseModel):
    version_id: str = Field(..., description="ID of the verified version to promote to active")
    approval_id: str | None = Field(default=None, description="Optional human approval record ID if required by policy")


class EndpointRollbackRequest(BaseModel):
    reason: str = Field(default="Manual rollback to last known good version")
