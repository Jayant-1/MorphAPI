# MorphAPI Architectural Decision Records (ADRs)

## 1. Index of Decisions

- [ADR-001: Model Is Not the Verifier](#adr-001-model-is-not-the-verifier)
- [ADR-002: Shared Extraction Engine for REST and MCP Protocols](#adr-002-shared-extraction-engine-for-rest-and-mcp-protocols)
- [ADR-003: Dual-Mode Client Architecture with Offline Simulation Fixtures](#adr-003-dual-mode-client-architecture-with-offline-simulation-fixtures)
- [ADR-004: Human-in-the-Loop Interrupt Gate for Selector Promotions](#adr-004-human-in-the-loop-interrupt-gate-for-selector-promotions)
- [ADR-005: Separation of Resumable Workflow Checkpoints from Authoritative Registry](#adr-005-separation-of-resumable-workflow-checkpoints-from-authoritative-registry)

---

## ADR-001: Model Is Not the Verifier

### Status
**Accepted**

### Context & Problem Statement
Generative AI models are capable of inspecting HTML markup and hypothesizing CSS or XPath selectors. However, LLMs suffer from hallucinations, cannot execute JavaScript on rendered pages, and often propose selectors that look syntactically plausible but match zero DOM nodes or match unintended elements in production. If the model's claim that a selector works is accepted as truth, downstream data consumers receive corrupted or empty payloads.

### Decision
The language model is treated solely as an investigator and proposal generator. Under no circumstances can the model mark a candidate selector as verified or active. Verification must be performed deterministically by executing the candidate selector in a headless browser (Playwright) against the live target page and validating the extracted values against strict Pydantic v2 schemas.

### Consequences & Benefits
- **Guaranteed Contract Reliability**: Only configurations proven to match elements and satisfy data schemas can handle live traffic.
- **Zero Hallucination Leakage**: Model errors are caught before reaching the configuration registry.
- **Auditability**: Every activated selector has an associated verification record showing real match counts and sample values.

### Alternatives Considered & Rejected
- *LLM-as-a-Judge*: Having a second model inspect the extracted text. Rejected because it incurs high API token costs, high latency, and fails to catch subtle structural type discrepancies.

---

## ADR-002: Shared Extraction Engine for REST and MCP Protocols

### Status
**Accepted**

### Context & Problem Statement
MorphAPI serves two distinct consumer audiences: traditional applications consuming REST JSON APIs and autonomous AI assistants consuming Model Context Protocol (MCP) tools. If REST and MCP maintain separate extraction codebases, inconsistencies will emerge in selector evaluation, caching, error codes, and validation logic.

### Decision
Both REST endpoints (`/api/v1/endpoints/{slug}/extract`) and MCP tool invocations (`extract_endpoint_data`) call the **exact same internal extraction service**. MCP is implemented as a thin protocol adapter that translates incoming JSON-RPC 2.0 tool calls into shared service calls.

### Consequences & Benefits
- **100% Contract Parity**: REST clients and MCP AI assistants receive identical extracted data and identical error semantics.
- **Single Source of Truth**: Selector optimizations, bug fixes, and security patches apply simultaneously to both interfaces.
- **Maintainability**: Eliminates duplicate browser automation code.

### Alternatives Considered & Rejected
- *Dedicated MCP Microservice*: Building a standalone Python server for MCP. Rejected due to code duplication and operational complexity.

---

## ADR-003: Dual-Mode Client Architecture with Offline Simulation Fixtures

### Status
**Accepted**

### Context & Problem Statement
Frontend developers, designers, and hackathon evaluators need to inspect, test, and demonstrate complex user workflows (such as AST selector mutation diffing, fracture recovery, and MCP tool execution) even in standalone environments where backend browser workers or external LLM credentials might not be configured.

### Decision
The frontend `ApiClient` implements a dual-mode data architecture governed by an interactive toggle in the sidebar (`MOCK FIXTURE` vs. `LIVE REST`). When in Demo Mode, the client uses a comprehensive, realistic fixture suite (`demo-fixtures.ts`) combined with in-browser `localStorage` persistence. When Live Mode is selected, requests are routed transparently to the FastAPI control plane over HTTP.

### Consequences & Benefits
- **Zero-Friction Evaluation**: Reviewers can immediately test all 12 routes and trigger simulated self-healing without provisioning infrastructure.
- **Clean Drop-In Interface**: Page components use identical TypeScript interfaces regardless of whether data originates from fixtures or live REST.
- **Rapid UI Iteration**: UI development proceeds without requiring an active browser worker pool.

### Alternatives Considered & Rejected
- *Hardcoded Mock Pages*: Separate mock routes (e.g. `/mock/dashboard`). Rejected because it bifurcates the codebase and leads to stale demo implementations.

---

## ADR-004: Human-in-the-Loop Interrupt Gate for Selector Promotions

### Status
**Accepted**

### Context & Problem Statement
While autonomous self-healing is fast, promoting modified selectors directly to production without oversight can lead to silent schema drifts if an external website undergoes a radical restructuring (such as changing a price field from including tax to excluding tax).

### Decision
LangGraph workflows implement an explicit **Human Approval Interrupt Gate**. When a repaired selector passes browser verification, the workflow generates a unified AST selector diff and pauses execution. The endpoint is marked in degraded/needs-attention status until a human operator reviews the diff in the console (`/agent-runs/[id]`) and clicks `[APPROVE & PROMOTE TO V2]`. Automated promotion can be enabled optionally via tenant policy (`REQUIRE_APPROVAL=false`).

### Consequences & Benefits
- **Human Oversight**: Operators retain final authority over production schema mutations.
- **Visual Diff Transparency**: The unified diff viewer clearly contrasts the broken selector (`-`) against the verified replacement (`+`).
- **Resumable State**: LangGraph checkpoints preserve workflow state across browser sessions while awaiting operator action.

### Alternatives Considered & Rejected
- *Immediate Unconditional Auto-Promotion*: Always promoting validated candidates. Rejected because semantic data changes require human validation for enterprise SLAs.

---

## ADR-005: Separation of Resumable Workflow Checkpoints from Authoritative Registry

### Status
**Accepted**

### Context & Problem Statement
LangGraph workflows require frequent state snapshots (serialized tool messages, intermediate candidate arrays, and execution counters) to enable resumption after interrupts or transient network drops. Mixing this transient, high-churn workflow state with the core business database creates table bloat, complicated migrations, and concurrency locks.

### Decision
MorphAPI explicitly separates the **Authoritative Business Registry** (PostgreSQL/SQLite) from the **Workflow Checkpointer** (Redis/dedicated checkpointer). Business records (endpoints, immutable versions, audit logs) are updated only via atomic transactions upon explicit lifecycle milestones.

### Consequences & Benefits
- **Decoupled Lifecycles**: Workflow checkpoints can be safely pruned after 14 days without affecting endpoint version history.
- **ACID Integrity**: Business records remain clean, normalized, and protected from workflow retry turbulence.
- **Independent Scaling**: Checkpointing storage can be backed by fast in-memory key-value stores (Redis) while business data resides in relational storage.

### Alternatives Considered & Rejected
- *Unified Monolithic Database*: Storing LangGraph thread state directly inside the business `endpoints` table. Rejected due to schema bloat and high write contention.
