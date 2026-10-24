# Seven-Agent End-to-End Workflow

## Phase 0 — Contract freeze (Agent 1, first 30–45 minutes)
Read the SRS/UML. Approve route names, shared models, database schema, telemetry, MCP transport, and NIM configuration. Commit shared contracts, stubs, `.env.example`, and startup commands before specialist agents diverge.

## Parallel implementation
- Agent 1: architecture, shared contracts, integration, documentation.
- Agent 2: registration API, SQLite registry, selector/audit persistence.
- Agent 3: Playwright extraction, schema compiler/validator, typed failures.
- Agent 4: DOM pruning, screenshots, NIM/DeepSeek client, patch parser.
- Agent 5: Next.js dashboard, mock portal, chaos toggle.
- Agent 6: MCP SDK/transport, tool discovery/invocation.
- Agent 7: tests, benchmarks, security review.

## Integration sequence
1. App starts; SQLite initializes.
2. Registry can register/read endpoint.
3. Deterministic extraction works against local fixture with no model call.
4. Orchestrator exposes REST extraction.
5. Fake model heals redesigned portal; candidate patch is verified and persisted.
6. Real NIM multimodal call works with screenshot + pruned DOM.
7. Dashboard displays events and selector diff.
8. MCP invokes the same orchestrator.
9. QA runs concurrent healing, failure, security and performance tests.

## 12-hour suggested gates
- Hour 0–1: contracts and skeleton.
- Hour 1–3: registry + runner + UI mock in parallel.
- Hour 3–6: fast path; healing subsystem and MCP stubs progress in parallel.
- Hour 6–8: fake-model healing integrated.
- Hour 8–9: real NIM smoke test and UI wiring.
- Hour 9–10.5: MCP + end-to-end integration.
- Hour 10.5–12: regression, security, performance, demo rehearsal.

## Demo
1. Normal extraction -> FAST_PATH.
2. Toggle “Chaos: Redesign UI”.
3. Extraction fails selectors and emits HEALING_TRIGGERED.
4. Screenshot + pruned DOM go to DeepSeek through NVIDIA NIM.
5. Model proposes patch; Playwright and Pydantic verify.
6. Persist selectors and audit log; emit HEAL_COMPLETE.
7. Next request returns FAST_PATH.
8. Invoke same endpoint through MCP.

## Stop-the-line conditions
Pause and ask Agent 1 if routes/payloads disagree, shared files conflict, a patch can be persisted before verification, fast path calls NIM, MCP duplicates the extraction logic, or a merge breaks startup/smoke tests.
