# Healing Flow and Telemetry
1. REST/MCP calls shared orchestrator.
2. Load endpoint and selector version.
3. Run cached Playwright selectors and validate with dynamic Pydantic model.
4. If valid, return `FAST_PATH`; do not call NIM.
5. If selector failure/schema mismatch, acquire per-endpoint async lock and re-check current selectors.
6. Capture screenshot + pruned DOM, then call NIM/DeepSeek adapter.
7. Parse strict JSON candidate patch; reject malformed output.
8. Re-run extraction and schema validation.
9. Only on success, atomically persist selectors/version/audit log and return `SELF_HEALED`.
10. Allow one bounded retry with sanitized error feedback; then mark DEGRADED and return controlled error.

Event names: `EXTRACTION_STARTED`, `FAST_PATH_OK`, `HEALING_TRIGGERED`, `HEALING_CONTEXT_CAPTURED`, `HEALING_PATCH_PROPOSED`, `HEAL_COMPLETE`, `HEALING_FAILED`, `ENDPOINT_STATUS_CHANGED`.

Event payload must include `event_type`, UTC ISO timestamp, `endpoint_id`, request/correlation ID when available, status/message, optional latency and selector diff. Avoid broadcasting large base64 screenshots repeatedly; use protected retrieval or a separate payload. Never stream secrets, cookies, PII, raw prompts, or stack traces.
