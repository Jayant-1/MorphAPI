# MorphAPI

**Self-healing Web-to-API and MCP gateway**

MorphAPI turns a customer-defined website and response schema into a reusable, verified API endpoint. It uses a real browser to inspect and extract website data, deterministic backend checks to validate results, and a bounded agentic workflow to discover or repair selectors when the website changes.

## What the application does

A customer provides:
1. A target URL and any allowed URL scope.
2. A desired output schema (for example, product title, price, availability, or article headline).
3. Optional extraction hints, authentication instructions, locale, and refresh expectations.

MorphAPI inspects the page, proposes selectors, tests those selectors in Playwright, extracts actual sample values, validates those values against the customer's schema and configured rules, and asks for clarification or approval when needed. Only configurations that pass backend-owned verification can be activated.

After activation, the customer can call the generated endpoint through REST or an MCP tool. Both interfaces use the same extraction service and verified configuration registry.

## Architecture in one sentence

**Next.js UI → FastAPI control plane → verified endpoint registry + shared extraction service → Playwright browser workers; Deep Agents proposes and investigates, LangGraph runs durable workflows, NVIDIA NIM provides the configured model, and deterministic backend services decide whether a configuration is safe to activate.**

## Key capabilities

- Website-to-API onboarding from a URL and user-defined JSON schema.
- Browser-backed page inspection using Playwright, including rendered DOM and dynamic content.
- Selector proposal and bounded selector testing with actual extracted values.
- Deep Agents harness for multi-step planning, tool selection, evidence management, and optional isolated subtask delegation.
- LangGraph workflow runtime for state, checkpoints, resumable work, explicit branching, bounded retries, and human approval interrupts.
- NVIDIA NIM model provider adapter, with explicit model configuration and a tool-calling compatibility preflight.
- Deterministic extraction validation using Pydantic v2 and application-owned checks.
- Self-healing when an active selector stops working, with versioned candidate evaluation and rollback to a last-known-good configuration when available.
- Shared REST and MCP execution path; no separate extraction implementation for MCP.
- Audit events, structured logs, traceable healing attempts, and integration acceptance tests.
- Three-person implementation split with stable contracts and a documented integration sequence.

## Core safety and correctness rules

1. **The model is not the verifier.** A model-generated claim that a selector works is not proof. The backend must run it against the real browser and inspect actual values.
2. **The schema is customer-owned.** Agent proposals cannot silently modify required fields, types, or validation rules.
3. **Only verified configurations activate.** Persist candidates separately from active configurations; promote only after deterministic checks pass.
4. **Fast path stays fast.** A successful extraction with a verified selector must not call the LLM, Deep Agents, or the healing workflow.
5. **One extraction engine.** REST and MCP call the same shared service and produce the same contract.
6. **Bounded autonomy.** Limit browser actions, tool calls, graph steps, retries, time, and resource usage. Ask for human input when the evidence is insufficient.
7. **Least privilege.** Do not expose arbitrary shell execution, unrestricted network access, or direct database writes to the agent. Give it only narrow MorphAPI tools.
8. **Real integration tests.** Tests must prove browser extraction, NIM tool-calling, validation, persistence, REST, and MCP behavior. Do not fake successful integration results.
9. **External websites are untrusted.** Page text, scripts, and embedded instructions must never override system policy or tool permissions.
10. **No model fallback by accident.** The configured NVIDIA NIM endpoint/model is explicit. If compatibility checks fail, disable agentic activation rather than silently switching models.

## Technology baseline

- **Frontend:** Next.js, React, TypeScript, Tailwind CSS.
- **API/control plane:** Python, FastAPI, Pydantic v2.
- **Browser extraction:** Playwright; BeautifulSoup/lxml may help parse static HTML but does not replace browser-backed verification for dynamic sites.
- **Agent harness:** `deepagents` for planning, context management, tool use, and optional subagent delegation.
- **Workflow runtime:** LangGraph for durable execution, checkpoints, controlled branches, and human-in-the-loop interrupts.
- **Model provider:** NVIDIA NIM through a provider adapter. Verify the exact model and endpoint support for required tool calling before enabling the workflow.
- **Persistence:** SQLite for local development and initial single-instance use; define a migration path to a production database before multi-instance deployment. LangGraph checkpoint storage is separate from the business registry.
- **Protocol:** REST/JSON plus MCP tools over a shared extraction service.
- **Tests:** unit, contract, Playwright integration, NIM compatibility, workflow-resume, REST/MCP parity, and end-to-end acceptance tests.

## Repository guide

- [`document-index.md`](document-index.md) — master file-by-file guide and reading maps
- [`system-overview.md`](system-overview.md) — executive summary, problem statement, and APMC Mandi pricing demo
- [`tech-stack.md`](tech-stack.md) — complete technology stack matrix and dependencies
- [`architecture.md`](architecture.md) — complete system architecture, component boundaries, and high-level design
- [`frontend-architecture.md`](frontend-architecture.md) — Next.js 15 App Router design, UI instrument aesthetic, and AST diff engine
- [`api-and-mcp-specification.md`](api-and-mcp-specification.md) — REST endpoint contracts and Model Context Protocol (MCP) tool bindings
- [`database-schema.md`](database-schema.md) — business entity-relationship models, versioning, and persistence contracts
- [`self-healing-and-agentic-workflow.md`](self-healing-and-agentic-workflow.md) — LangGraph state transitions, Playwright selector verification, and human approval gates
- [`security-and-isolation.md`](security-and-isolation.md) — SSRF firewall, browser sandboxing, prompt injection defenses, and scoped tools
- [`setup-and-deployment.md`](setup-and-deployment.md) — local setup instructions, environment variables, and Docker Compose topology
- [`testing-and-verification.md`](testing-and-verification.md) — multi-tier testing strategy, release gates, and REST/MCP parity tests
- [`architectural-decisions.md`](architectural-decisions.md) — formal Architectural Decision Records (ADRs 001 - 005)
- [`requirements.md`](requirements.md) — functional and non-functional requirements and acceptance criteria

## Suggested implementation sequence

1. Agree on shared Pydantic contracts, status/error model, database ownership, and endpoint lifecycle.
2. Build the deterministic extraction service and Playwright selector tester first.
3. Build the FastAPI registry/control plane and REST extraction path.
4. Implement the NVIDIA NIM adapter and run tool-calling compatibility tests with the exact configured model.
5. Add the Deep Agents harness only to discovery/healing paths, with narrow tools and no direct write privileges.
6. Add explicit LangGraph workflow state, persistent checkpointer, retry budgets, interrupts, and idempotent side effects.
7. Add MCP tools as a thin adapter to the shared service.
8. Build the frontend onboarding, verification evidence, activation, status, and healing history views.
9. Run REST/MCP parity and end-to-end acceptance tests against a real test website and actual configured NIM endpoint.
10. Review secrets, browser isolation, SSRF controls, quotas, observability, backups, and production database needs before deployment.

## Important scope note

MorphAPI does not create a new Python server for every customer. It runs a **shared dynamic gateway** that stores verified endpoint configurations and routes requests through a common extraction engine. This keeps customer endpoints versionable, observable, testable, and consistent.
