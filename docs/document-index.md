# MorphAPI Documentation Index

Welcome to the comprehensive technical documentation for **MorphAPI**, an autonomous self-healing Web-to-API and Model Context Protocol (MCP) gateway.

---

## Document Directory

| Document | Description | Target Audience | Status |
|---|---|---|---|
| [System Overview](system-overview.md) | Executive summary, problem statement, core capabilities, and real-world agricultural use case | All / Product Engineers | Complete |
| [Architecture Specification](architecture.md) | Comprehensive system architecture, component boundaries, and high-level design | Core & Systems Architects | Complete |
| [Technology Stack](tech-stack.md) | In-depth breakdown of frontend and control plane libraries, runtimes, and dependencies | Developers / DevOps | Complete |
| [Frontend Architecture](frontend-architecture.md) | Next.js 15 App Router design, UI instrument aesthetic, dual-mode client, and interactive AST diff engine | Frontend Engineers | Complete |
| [API & MCP Specification](api-and-mcp-specification.md) | Complete REST endpoint contracts, Model Context Protocol (MCP) tool bindings, and JSON-RPC 2.0 schemas | API Consumers / AI Developers | Complete |
| [Database Schema & Models](database-schema.md) | Relational database schema, entity-relationship models, versioning records, and audit ledgers | Database Engineers / Backend | Complete |
| [Self-Healing & Agentic Workflow](self-healing-and-agentic-workflow.md) | LangGraph state transitions, Playwright selector verification, and human-in-the-loop approval gates | AI & Automation Engineers | Complete |
| [Security & Isolation](security-and-isolation.md) | SSRF defense, headless browser sandboxing, prompt injection defenses, and least-privilege tools | Security / Platform Engineers | Complete |
| [Setup & Deployment](setup-and-deployment.md) | Local development setup, environment variables reference, Docker Compose topology, and production scaling | DevOps / Developers | Complete |
| [Testing & Verification](testing-and-verification.md) | Multi-tier test strategy, preflight checks, REST/MCP parity tests, and build verification | QA & Test Engineers | Complete |
| [Architectural Decision Records (ADRs)](architectural-decisions.md) | Formal ADRs detailing key technical decisions, rationale, alternatives, and trade-offs | Architects / Engineering Leads | Complete |
| [System Requirements](requirements.md) | Functional (FR) and non-functional (NFR) requirements and acceptance criteria | Product Managers / Leads | Complete |
| [Repository Guide (Legacy)](readme.md) | Historical three-person implementation plan and integration guidelines | Maintainers | Preserved |

---

## Suggested Reading Paths

### 1. New Developer Onboarding
1. [System Overview](system-overview.md): Understand what MorphAPI does and how it eliminates scraper downtime.
2. [Technology Stack](tech-stack.md): Review language versions, frameworks, and core dependencies.
3. [Setup & Deployment](setup-and-deployment.md): Clone the repository and boot the Next.js control plane.
4. [Frontend Architecture](frontend-architecture.md): Explore the 12 routes, UI components, and the dual-mode data layer.

### 2. AI Assistant & MCP Integration
1. [API & MCP Specification](api-and-mcp-specification.md): Review the Model Context Protocol tools and SSE transports.
2. [Self-Healing & Agentic Workflow](self-healing-and-agentic-workflow.md): Learn how the agent repairs broken selectors autonomously.
3. [Security & Isolation](security-and-isolation.md): Verify network boundaries and SSRF restrictions.

### 3. Backend & Core Architecture
1. [Architecture Specification](architecture.md): Understand component boundaries between FastAPI, Playwright, and LangGraph.
2. [Database Schema & Models](database-schema.md): Inspect relational entities, versioning, and immutable audit logs.
3. [Architectural Decision Records (ADRs)](architectural-decisions.md): Review fundamental decisions (e.g. Model is not the verifier).
4. [Testing & Verification](testing-and-verification.md): Review release gates and parity tests.

---

## Implementation Status Disclaimer

MorphAPI's user interface, interactive AST mutation engine, REST playground, MCP test bench, and dual-mode client layer are **fully implemented, verified, and running** in `Frontend/`. The backend control plane services (FastAPI router, Playwright worker pool, LangGraph healing graph, and NVIDIA NIM adapter) are documented as **Architectural Implementation Contracts** based on the product specifications.
