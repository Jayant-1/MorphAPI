# Integration Runbook
1. Agent 1 approves decisions and commits shared contracts/stubs.
2. Start app + initialize SQLite.
3. Integrate registry and registration API.
4. Integrate deterministic Playwright extraction and schema validation.
5. Integrate orchestrator and REST route.
6. Prove fake-model healing against local mock portal.
7. Add NIM client and live multimodal smoke test.
8. Wire dashboard and telemetry.
9. Integrate MCP against the shared orchestrator.
10. Run QA/security/performance suite and rehearse.

Smoke test: register `pune_mandi` against local portal; extract legacy table -> FAST_PATH; toggle redesigned UI; trigger healing; verify candidate selectors; persist only after validation; extract again -> FAST_PATH; invoke via MCP.

Merge gate: tests pass, contract matches, handoff is complete, app starts, smoke test passes. If live NIM is down, use fake model only as a clearly labeled offline fallback.
