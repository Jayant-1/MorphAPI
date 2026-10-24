"""
MorphAPI Core Contracts & Data Models
Canonical contracts shared between Person 1 (Backend/Registry), Person 2 (Browser Automation & Agentic Systems), and Person 3 (Frontend & MCP).
"""

from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, Field, HttpUrl, field_validator

from morphapi.schemas.errors import FailureCode

EndpointStatus = Literal[
    "DRAFT",
    "INSPECTING",
    "CANDIDATE_READY",
    "VERIFIED",
    "ACTIVE",
    "DEGRADED",
    "HEALING",
    "NEEDS_APPROVAL",
]

ExecutionPath = Literal["FAST_PATH", "SELF_HEALED"]


class SelectorPatch(BaseModel):
    """
    A proposed selector configuration from the agent/model.
    Note: The model can propose patches, but only backend deterministic checks can verify them.
    """
    new_selectors: dict[str, str] = Field(..., description="Field-to-selector mapping")
    ai_reasoning: str = Field(..., description="Concise explanation of the selector choices")
    confidence_score: float | None = Field(default=None, ge=0.0, le=1.0)
    evidence_refs: list[str] = Field(default_factory=list, description="References to page evidence used")

    @field_validator("new_selectors")
    @classmethod
    def validate_selectors_not_empty(cls, v: dict[str, str]) -> dict[str, str]:
        if not v:
            raise ValueError("new_selectors dictionary cannot be empty")
        for key, sel in v.items():
            if not sel or not isinstance(sel, str) or not sel.strip():
                raise ValueError(f"Selector for field '{key}' cannot be empty")
        return v


class FieldEvidence(BaseModel):
    """Structured evidence for a single field extraction."""
    field_name: str
    selector: str
    matched_count: int
    sample_values: list[Any] = Field(default_factory=list)
    tag_name: str | None = None
    is_visible: bool = True
    error: str | None = None


class ValidationResult(BaseModel):
    """Deterministic validation result produced by backend code."""
    is_valid: bool
    normalized_data: Any = None
    errors: list[str] = Field(default_factory=list)
    field_evidences: list[FieldEvidence] = Field(default_factory=list)


class ExtractionResult(BaseModel):
    """Structured result returned by the browser extraction service."""
    success: bool
    data: Any = None
    field_evidences: list[FieldEvidence] = Field(default_factory=list)
    validation: ValidationResult | None = None
    page_title: str | None = None
    target_url: str
    latency_ms: int
    error_code: FailureCode | None = None
    error_message: str | None = None
    evidence_ref: str | None = None


class ExtractionResponse(BaseModel):
    """Client-facing extraction response (REST / MCP shared contract)."""
    endpoint_id: str
    data: Any
    healed_this_request: bool
    execution_path: ExecutionPath
    latency_ms: int
    fetched_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    request_id: str | None = None
    config_version: int | None = None


class EndpointRegisterRequest(BaseModel):
    endpoint_id: str = Field(..., pattern=r"^[a-zA-Z0-9_-]{2,80}$")
    name: str = Field(..., min_length=1, max_length=200)
    target_url: HttpUrl
    schema_definition: dict[str, str] = Field(..., min_length=1)
    initial_selectors: dict[str, str] | None = None
    allowed_url_scope: list[str] = Field(default_factory=list)
