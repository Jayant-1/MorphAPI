# Shared Contracts for MorphAPI

Status: Approved / Canonical Contract between Person 1 (Backend/Registry) and Person 2 (Extraction & Self-Healing Engine).

## Core Data Types and Enums

```python
from typing import Any, Literal
from pydantic import BaseModel, Field, HttpUrl

EndpointStatus = Literal["HEALTHY", "HEALING", "DEGRADED", "AUTH_REQUIRED"]
ExecutionPath = Literal["FAST_PATH", "SELF_HEALED"]

class EndpointRegisterRequest(BaseModel):
    endpoint_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{2,80}$")
    name: str
    target_url: HttpUrl
    schema_definition: dict[str, str]
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

class ErrorResponse(BaseModel):
    error_code: str
    message: str
    endpoint_id: str | None = None
    retryable: bool = False
```

## Shared Telemetry Event Names
- `EXTRACTION_STARTED`
- `FAST_PATH_OK`
- `HEALING_TRIGGERED`
- `HEALING_CONTEXT_CAPTURED`
- `HEALING_PATCH_PROPOSED`
- `HEAL_COMPLETE`
- `HEALING_FAILED`
- `ENDPOINT_STATUS_CHANGED`

## REST Routes
- `POST /api/v1/endpoints/register` -> 201 + endpoint metadata
- `GET /api/v1/extract/{endpoint_id}` -> 200 + `ExtractionResponse`
- `GET /api/v1/endpoints` -> 200 + list of endpoints
- `GET /api/v1/endpoints/{id}/healing-logs` -> 200 + healing logs
- `WS /ws/telemetry` -> real-time WebSocket events
- `GET /api/v1/telemetry` -> polling fallback for events
- `GET /health` -> 200 health check

## Storage Contract (SQLite)
- `endpoints`: `id` (PK), `name`, `target_url`, `schema_json`, `selectors_json`, `status`, `version`, `last_verified`, `updated_at`.
- `healing_logs`: `log_id` (PK), `endpoint_id` (FK), `timestamp`, `failure_reason`, `old_selectors`, `new_selectors`, `ai_reasoning`, `screenshot_b64`, `heal_latency_ms`, `from_version`, `to_version`.
- `request_telemetry`: `id` (PK), `endpoint_id` (FK), `execution_path`, `latency_ms`, `tokens_used`, `http_status`, `timestamp`.
