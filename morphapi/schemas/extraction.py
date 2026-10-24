"""
MorphAPI Extraction Schemas
Defines request and response structures for deterministic extraction.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field
from morphapi.schemas.contracts import FieldEvidence, ValidationResult, ExecutionPath


class ExtractionRequest(BaseModel):
    query_params: dict[str, Any] = Field(default_factory=dict, description="Optional query parameters")
    bypass_cache: bool = Field(default=False, description="Whether to bypass cached result")
    correlation_id: str | None = Field(default=None, description="Client-supplied correlation ID")


class ExtractionResponse(BaseModel):
    """
    Standard extraction response returned identically by REST and MCP gateway.
    """
    endpoint_id: str
    data: Any
    healed_this_request: bool = False
    execution_path: ExecutionPath = "FAST_PATH"
    latency_ms: int
    fetched_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    request_id: str | None = None
    config_version: int | None = None
    field_evidence: list[FieldEvidence] = Field(default_factory=list)
