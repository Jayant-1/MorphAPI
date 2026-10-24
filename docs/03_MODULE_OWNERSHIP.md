# Module Ownership
| Agent | Owns | Avoid owning |
|---|---|---|
| 1 Tech Lead | shared contracts, app composition, config, integration docs/runbook | specialist internals without agreement |
| 2 Backend/Registry | registration routes, SQLite schema/repository, registry service | runner, AI internals, frontend |
| 3 Runner/Validator | Playwright runner, schema compiler/validator, runner tests | API routes, database schema, model client |
| 4 Healing/NIM | DOM pruner, screenshot context, NIM client, fake client, patch parser | DB writes, frontend, REST routes |
| 5 Frontend | Next.js dashboard, mock civic portal, chaos toggle | backend files |
| 6 MCP | MCP server/tool discovery/invocation | duplicate extraction or registry implementation |
| 7 QA/Security | test suites, fixtures, benchmark reports, security findings | production code without owner approval |

Shared files (`contracts.py`, `main.py`, config, orchestrator, telemetry schema, dependency manifests) are coordinated by Agent 1. Suggested branches: `agent-1-integration` through `agent-7-qa`.
