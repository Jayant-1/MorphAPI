"""
MorphAPI Audit Schemas
Defines immutable audit event types and event records.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class AuditEventType(str, Enum):
    ENDPOINT_CREATED = "ENDPOINT_CREATED"
    ENDPOINT_UPDATED = "ENDPOINT_UPDATED"
    CANDIDATE_SUBMITTED = "CANDIDATE_SUBMITTED"
    CANDIDATE_VERIFIED = "CANDIDATE_VERIFIED"
    CANDIDATE_REJECTED = "CANDIDATE_REJECTED"
    VERSION_ACTIVATED = "VERSION_ACTIVATED"
    ROLLBACK_TRIGGERED = "ROLLBACK_TRIGGERED"
    EXTRACTION_SUCCESS = "EXTRACTION_SUCCESS"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    HEALING_TRIGGERED = "HEALING_TRIGGERED"
    HEALING_COMPLETED = "HEALING_COMPLETED"
    HEALING_FAILED = "HEALING_FAILED"
    APPROVAL_REQUESTED = "APPROVAL_REQUESTED"
    APPROVAL_RESOLVED = "APPROVAL_RESOLVED"
    POLICY_EVALUATED = "POLICY_EVALUATED"
    POLICY_BLOCKED = "POLICY_BLOCKED"


class AuditEvent(BaseModel):
    audit_id: int | None = None
    correlation_id: str = Field(..., description="Correlation ID for distributed tracing")
    tenant_id: str = Field(default="default_tenant")
    actor: str = Field(default="system")
    action: AuditEventType
    target_type: str = Field(..., description="E.g. endpoint, version, job")
    target_id: str
    details: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AuditListResponse(BaseModel):
    endpoint_id: str
    events: list[AuditEvent] = Field(default_factory=list)
    total_count: int
