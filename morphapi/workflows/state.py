"""
MorphAPI LangGraph Typed Workflow State
Durable state schema for LangGraph agentic discovery and self-healing.
Stores references to large sanitized evidence rather than unbounded DOM dumps.
"""

from typing import Any, Literal, TypedDict

WorkflowStatus = Literal[
    "INITIALIZED",
    "CHECKING_POLICY",
    "INSPECTING",
    "PROPOSING",
    "TESTING",
    "VALIDATING",
    "DIAGNOSING",
    "AWAITING_APPROVAL",
    "AWAITING_USER",
    "PROMOTED",
    "FAILED",
]


class WorkflowState(TypedDict, total=False):
    """
    Typed graph state for LangGraph self-healing and discovery.
    """
    endpoint_id: str
    target_url: str
    schema_definition: dict[str, str]
    active_selectors: dict[str, str]
    candidate_selectors: dict[str, str] | None
    ai_reasoning: str | None
    confidence_score: float | None

    # Large evidence is stored by reference ID to prevent unbounded graph state
    evidence_refs: list[str]
    page_title: str | None

    # Bounded execution metrics
    attempt_count: int
    max_attempts: int
    tool_call_count: int
    max_tool_calls: int
    deadline_ts: float

    # Deterministic outcomes
    is_verified: bool
    status: WorkflowStatus
    error_context: str | None
    validation_errors: list[str]
    sample_data: Any

    # Human-in-the-loop and interrupts
    requires_approval: bool
    approval_granted: bool | None
    user_clarification: str | None

    # Idempotency and audit tracking
    workflow_id: str
    version_promoted: int | None
    promoted_at: str | None
    audit_log: list[dict[str, Any]]
