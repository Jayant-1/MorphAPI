# Test and Acceptance Plan
Test layers: unit, integration, contract, end-to-end, MCP, security, and performance.

Must pass:
- Valid registration works; invalid input gets structured errors.
- Endpoint and selectors persist across restart.
- Legacy fixture extracts valid JSON and arrays correctly.
- Missing selectors or schema-invalid output triggers healing, not false success.
- Candidate patch is never persisted until extraction + schema validation pass.
- Successful patch increments selector version and writes audit record.
- Concurrent requests to the same broken endpoint launch at most one healing cycle.
- NIM timeout, rate limit, auth error, or malformed JSON produces controlled failure.
- MCP uses same orchestrator as REST.
- Dashboard tolerates disconnected telemetry.
- URL/SSRF checks and secret redaction are tested.

Measure SRS targets rather than assuming them: fast path <=250 ms excluding upstream TTFB; healing <=5 seconds; DOM reduction >=80% while preserving visible text and id/class. Record machine, browser setup, sample count, target TTFB, model ID, and provider latency.
