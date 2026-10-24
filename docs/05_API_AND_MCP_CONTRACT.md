# REST and MCP Contract
Proposed REST routes:
- `POST /api/v1/endpoints/register` -> 201 + endpoint metadata.
- `GET /api/v1/extract/{endpoint_id}` -> 200 + `ExtractionResponse`.
- Unknown endpoint -> 404; unrecoverable target mutation after bounded healing -> controlled 502.
- `WS /ws/telemetry` for live events; `GET /api/v1/telemetry` may be a polling fallback.

MCP: Agent 6 must pin SDK and transport with Agent 1. Implement tool discovery and invocation using the same shared orchestrator as REST. Do not duplicate scraping/healing logic. Add a real SDK/client smoke test. SRS and UML differ on MCP paths and SSE/Stdio; do not claim compatibility until the selected transport is tested.
