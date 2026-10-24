"""
MorphAPI Workflow & Telemetry Contracts
Shared contracts for LangGraph durable workflows, job state, interrupts, and audit events.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, Field

TelemetryEventType = Literal[
    "EXTRACTION_STARTED",
    "FAST_PATH_OK",
    "HEALING_TRIGGERED",
    "HEALING_CONTEXT_CAPTURED",
    "HEALING_PATCH_PROPOSED",
    "HEAL_COMPLETE",
    "HEALING_FAILED",
    "ENDPOINT_STATUS_CHANGED",
    "APPROVAL_REQUESTED",
    "APPROVAL_RESOLVED",
    "BUDGET_EXCEEDED",
]


class JobType(str, Enum):
    DISCOVERY = "DISCOVERY"
    HEALING = "HEALING"


class JobStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    PAUSED_FOR_APPROVAL = "PAUSED_FOR_APPROVAL"
    PAUSED_FOR_CLARIFICATION = "PAUSED_FOR_CLARIFICATION"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class WorkflowTelemetryEvent(BaseModel):
    event_type: TelemetryEventType
    endpoint_id: str
    workflow_id: str | None = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    message: str
    latency_ms: int | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class ClarificationRequest(BaseModel):
    """Created when the workflow pauses for human operator clarification."""
    question: str
    choices: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    field_name: str | None = None


class CandidateSubmission(BaseModel):
    """A draft candidate selector configuration submitted by the agent for verification."""
    draft_id: str
    selector_map: dict[str, str]
    rationale: str
    evidence_refs: list[str] = Field(default_factory=list)


class JobResponse(BaseModel):
    job_id: str
    endpoint_id: str
    tenant_id: str
    job_type: JobType
    workflow_thread_id: str | None = None
    status: JobStatus
    attempt_count: int = 1
    max_attempts: int = 3
    failure_reason: str | None = None
    result_summary: dict[str, Any] = Field(default_factory=dict)
    clarification: ClarificationRequest | None = None
    created_at: str
    updated_at: str


class JobResumeRequest(BaseModel):
    approval_decision: Literal["approve", "reject"] | None = None
    clarification_response: str | None = None
    override_selectors: dict[str, str] | None = None
