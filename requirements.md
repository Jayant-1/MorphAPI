# MorphAPI Requirements

## 1. Purpose

Define the minimum functional and non-functional behavior for MorphAPI, a shared Web-to-API and MCP gateway with bounded, verified self-healing.

## 2. Functional requirements

### Endpoint authoring
- FR-001: A user can submit a target URL and desired output schema.
- FR-002: A user can provide field descriptions, extraction hints, and allowed URL scope.
- FR-003: The system validates request syntax and creates a draft, not an active endpoint.
- FR-004: The system shows discovery job status and errors.
- FR-005: The system displays candidate selectors, actual sample values, and field-level validation evidence.

### Browser inspection and extraction
- FR-010: The system uses Playwright to inspect rendered DOM when browser rendering is needed.
- FR-011: The system tests selectors against a real page and records actual match counts and sample values.
- FR-012: The system supports bounded waits, navigation timeouts, browser cleanup, and isolated contexts.
- FR-013: The system rejects disallowed URLs, redirects, and network destinations before or during browser access.
- FR-014: Extraction is deterministic given the page state, selector configuration, and normalization rules, subject to website volatility.

### Validation and activation
- FR-020: The backend validates extracted values against the user's schema using Pydantic v2 and explicit field rules.
- FR-021: The model cannot mark a candidate verified or active.
- FR-022: Invalid candidates remain non-active and retain diagnostic outcomes.
- FR-023: Verified configurations are versioned.
- FR-024: Promotion to active is an atomic backend-controlled operation.
- FR-025: Schema changes create a new version and require re-verification.
- FR-026: A last-known-good version is preserved according to retention policy.

### Agentic discovery and healing
- FR-030: Deep Agents is used only for discovery/healing paths, not normal successful extraction.
- FR-031: The agent can use only explicitly registered, typed MorphAPI tools.
- FR-032: The workflow has hard bounds for attempts, tool calls, candidates, wall-clock time, and per-tool timeouts.
- FR-033: LangGraph persists workflow checkpoints and supports resume after an interruption or recoverable failure.
- FR-034: The workflow can pause for human clarification/approval and validate the resumed input.
- FR-035: Every proposed repair is tested in Playwright and validated by backend code.
- FR-036: Failed healing results in a visible degraded/needs-attention state, not fake success.
- FR-037: Side effects are idempotent across retries and resume.
- FR-038: Optional subagent delegation is disabled unless an independent task and bounded contract justify it.

### NVIDIA NIM
- FR-040: The provider adapter explicitly configures the base URL, model ID, and credential source.
- FR-041: Startup/readiness preflight checks required tool-call round trips against the configured endpoint/model.
- FR-042: A failed preflight marks agentic capability not ready; no silent model substitution is permitted.
- FR-043: Model timeouts, rate limits, malformed tool calls, and provider errors map to stable internal errors.

### REST and MCP
- FR-050: REST and MCP use the same extraction service.
- FR-051: Both interfaces enforce the same authorization, quota, URL policy, validation, and active-config rules.
- FR-052: Both interfaces expose consistent success data and stable error semantics.
- FR-053: MCP mutations are explicitly authorized and approval-gated where policy requires.
- FR-054: A successful active extraction does not call NIM or start Deep Agents/LangGraph.

### Audit and operations
- FR-060: The system emits audit events for endpoint creation, verification, activation, healing, approval, rollback, and terminal failure.
- FR-061: Each request and workflow has a correlation identifier.
- FR-062: Logs redact credentials and avoid unnecessary raw page content.
- FR-063: Health endpoints distinguish service liveness from dependency readiness.

## 3. Non-functional requirements

- NFR-001 Reliability: workflow retries are bounded and recoverable jobs can resume from persistent checkpoints.
- NFR-002 Correctness: no configuration becomes active without actual browser testing and deterministic validation.
- NFR-003 Security: URL fetches are protected against SSRF, redirects, DNS rebinding, and cross-tenant leakage.
- NFR-004 Least privilege: agent tools do not expose arbitrary shell, unrestricted network, or direct database writes.
- NFR-005 Observability: extraction and healing outcomes, latency, failures, and model/tool-call errors are measurable.
- NFR-006 Performance: normal verified extraction avoids model latency.
- NFR-007 Maintainability: REST and MCP share services and contracts.
- NFR-008 Portability: provider and persistence configuration are environment-driven and typed.
- NFR-009 Data integrity: version promotion and audit writes use transactional/idempotent operations.
- NFR-010 Resource control: browser, workflow, and model calls have time, memory, and concurrency limits.
- NFR-011 Privacy: retention of page evidence and extracted data is explicit and configurable.
- NFR-012 Testability: core logic is unit-testable without live external services, while release gates include real provider/browser acceptance tests.

## 4. Acceptance criteria

A release candidate is acceptable only if:
- A user can create a draft from a URL and schema.
- A real Playwright session extracts actual sample values.
- Deterministic validation accepts a valid candidate and rejects an invalid one.
- Only a verified candidate can be activated.
- A known selector break starts a bounded workflow and either promotes a verified repair or leaves the endpoint degraded.
- The exact configured NIM endpoint/model passes tool-calling preflight.
- A checkpointed workflow resumes without duplicate activation side effects.
- REST and MCP return equivalent results/errors for the same active endpoint.
- Successful extraction does not call the model or workflow.
- SSRF and prompt-injection tests demonstrate that untrusted pages cannot access internal resources or override tool policy.
- Failure paths are visible and never reported as successful extraction.
