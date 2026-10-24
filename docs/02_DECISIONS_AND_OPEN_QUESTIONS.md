# Decisions and Open Questions
Status: proposals require Agent 1 approval.

- D-001 REST route: canonical proposal `POST /api/v1/endpoints/register` and `GET /api/v1/extract/{endpoint_id}`. UML also mentions `/api/v1/data/:id`; do not implement both unless approved.
- D-002 Registration schema field: use `schema_definition` in code. SRS also says `schema_spec`; resolve once and document any compatibility alias.
- D-003 Response healing flag: use `healed_this_request`; UML examples also use `healed`.
- D-004 MCP: Agent 1 and Agent 6 must select and pin SDK, protocol version, and transport. SRS and UML list different paths/transports.
- D-005 Database: include `endpoints`, `healing_logs`, and `request_telemetry` if Agent 1 approves the UML telemetry table.
- D-006 Model: NVIDIA NIM + a DeepSeek model. Confirm hosted vs self-hosted endpoint, exact model ID, and image input support.
- D-007 Registration without selectors: initial discovery is described in the SRS. Decide whether it runs synchronously or is deferred for the 12-hour MVP.
- D-008 CAPTCHA/HITL is medium priority; defer until the core healing demo works.
- D-009 Performance targets are targets, not guarantees: fast path <=250 ms excluding upstream TTFB; healing <=5 seconds; DOM character reduction >=80% while preserving visible text and structural id/class attributes.
