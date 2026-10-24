"""
MorphAPI Shared Contracts & Data Models
Canonical contract shared between Person 1 (Backend/Registry) and Person 2 (Extraction & Self-Healing).
"""

from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, Field, HttpUrl, field_validator

# Endpoint lifecycle statuses
EndpointStatus = Literal["HEALTHY", "HEALING", "DEGRADED", "AUTH_REQUIRED"]

# Execution path observed during extraction
ExecutionPath = Literal["FAST_PATH", "SELF_HEALED"]

# Canonical Telemetry Events
HealingEventType = Literal[
    "EXTRACTION_STARTED",
    "FAST_PATH_OK",
    "HEALING_TRIGGERED",
    "HEALING_CONTEXT_CAPTURED",
    "HEALING_PATCH_PROPOSED",
    "HEAL_COMPLETE",
    "HEALING_FAILED",
    "ENDPOINT_STATUS_CHANGED",
]


class EndpointRegisterRequest(BaseModel):
    endpoint_id: str = Field(..., pattern=r"^[a-zA-Z0-9_-]{2,80}$")
    name: str = Field(..., min_length=1, max_length=200)
    target_url: HttpUrl
    schema_definition: dict[str, str] = Field(..., min_length=1)
    initial_selectors: dict[str, str] | None = None


class ExtractionResponse(BaseModel):
    endpoint_id: str
    data: Any
    healed_this_request: bool
    execution_path: ExecutionPath
    latency_ms: int


class SelectorPatch(BaseModel):
    new_selectors: dict[str, str]
    ai_reasoning: str
    confidence_score: float | None = None

    @field_validator("new_selectors")
    @classmethod
    def validate_selectors_not_empty(cls, v: dict[str, str]) -> dict[str, str]:
        if not v:
            raise ValueError("new_selectors dictionary cannot be empty")
        for key, sel in v.items():
            if not sel or not isinstance(sel, str) or not sel.strip():
                raise ValueError(f"Selector for field '{key}' cannot be empty")
        return v


class ErrorResponse(BaseModel):
    error_code: str
    message: str
    endpoint_id: str | None = None
    retryable: bool = False


class TelemetryEvent(BaseModel):
    event_type: HealingEventType
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    endpoint_id: str
    request_id: str | None = None
    message: str
    latency_ms: int | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class FieldExtractionDiagnostic(BaseModel):
    field_name: str
    selector: str
    matched_count: int
    raw_value: Any = None
    normalized_value: Any = None
    error: str | None = None


class ExtractionDiagnostics(BaseModel):
    target_url: str
    started_at: str
    finished_at: str
    latency_ms: int
    field_diagnostics: list[FieldExtractionDiagnostic] = Field(default_factory=list)
    page_title: str | None = None
    errors: list[str] = Field(default_factory=list)


class ExtractionResult(BaseModel):
    success: bool
    data: Any = None
    diagnostics: ExtractionDiagnostics
    error_code: str | None = None
    error_message: str | None = None
    is_schema_valid: bool = False
    validation_errors: list[str] = Field(default_factory=list)
