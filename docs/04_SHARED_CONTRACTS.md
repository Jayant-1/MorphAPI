# Shared Contracts (Proposed)
Agent 1 approves before implementation.

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

Agree how selectors represent row/list selectors versus field selectors; do not assume a flat map handles every target. `data` may be an object or array according to endpoint configuration. `ai_reasoning` is a concise audit explanation, not hidden chain-of-thought. Never expose stack traces, keys, cookies, or raw prompts.
