# Software Requirements Specification (SRS)
## Project: MorphAPI — The Self-Healing Multimodal Web-to-API & MCP Gateway

**Version:** 1.0.0  
**Date:** October 24, 2026  
**Standard:** IEEE Std 830 / ISO/IEC/IEEE 29148 Compliant  
**License:** MIT Open-Source License  

---

## 1. Introduction

### 1.1 Purpose of the Document and Product
This Software Requirements Specification (SRS) provides a complete architectural and functional specification for **MorphAPI**, an open-source, self-healing Web-to-API and Model Context Protocol (MCP) gateway. 

The primary purpose of MorphAPI is to bridge the infrastructure gap between legacy, non-API web portals (such as state government resolution boards, agricultural Mandi price portals, and municipal grievance trackers) and modern software consumers (REST clients, WhatsApp/voice bots, and autonomous AI agents). When a target website alters its HTML/CSS layout, MorphAPI prevents downstream application failure by pausing the failing request, visually inspecting the broken page via an open-weight Multimodal Vision Language Model (VLM), rewriting its own CSS/XPath extraction selectors on the fly, validating the output against a strict schema, and returning a verified response.

### 1.2 Document Conventions and Intended Audience
* **Conventions:** Functional requirements are labeled sequentially as `FR-X.Y` and Non-Functional Requirements as `NFR-X.Y`. Priorities are categorized as **High (Critical for MVP)**, **Medium (Important for Stage Demo/Q&A)**, or **Low (Post-Hackathon Enhancement)**.
* **Intended Audience:** 
  * **Backend & AI Engineers:** Responsible for implementing the FastAPI proxy, Playwright execution engine, DOM AST pruner, and Vision LLM integration.
  * **Frontend Engineers:** Responsible for building the Next.js Mission Control telemetry dashboard and the local Mock Government Portal with the "Chaos UI" state toggle.
  * **Hackathon Evaluators & Open-Source Contributors:** Reviewing architectural rigor, model selection justification, and alignment with civic problem statements.

### 1.3 Project Scope and High-Level Objectives
* **In-Scope:**
  * A deterministic headless browser extraction engine (`Playwright`) backed by an SQLite selector cache for zero-token normal operation.
  * A runtime schema validation gate (`Pydantic`) that acts as an automated tripwire for structural drift or empty extractions.
  * An autonomous self-healing pipeline combining DOM Abstract Syntax Tree (AST) pruning and multimodal visual grounding (`Gemma 4` / Open-Weight VLM).
  * A native **Model Context Protocol (MCP)** server interface exposing registered web portals as structured tools for AI agents.
  * A real-time Next.js **Mission Control Dashboard** and a local **Mock Civic Portal** (simulating Maharashtra GR and MSAMB Mandi portals) with a one-click UI mutation trigger for deterministic live demonstrations.
* **High-Level Objectives:**
  * Eliminate scraper maintenance overhead for civic-tech developers building solutions for rural citizens and farmers (directly addressing Problem Statements #1, #6, #14, #15, and #16).
  * Achieve sub-second latency ($\le 250\text{ ms}$) during normal cached operations and sub-five-second recovery ($\le 5.0\text{ s}$) during autonomous self-healing events.

---

## 2. Overall Description

### 2.1 Product Perspective
MorphAPI operates as an intelligent middleware proxy situated between fragile HTML presentation layers and structured data consumers. Unlike traditional static web scrapers that crash with `HTTP 500` or return `null` when a webmaster renames a CSS class, and unlike pure LLM scrapers that burn thousands of tokens reading raw HTML on every single request, MorphAPI implements a **Dual-Path Execution Architecture**:

1. **Fast Deterministic Path ($99\%$ of traffic):** Executes cached CSS/XPath selectors via headless Playwright with $0$ LLM token consumption.
2. **Slow Multimodal Healing Path ($1\%$ of traffic — triggered only on UI mutation):** Invokes visual + structural AI recovery to patch the broken selector, updates the SQLite registry, and seamlessly resumes the Fast Path.

### 2.2 User Classes and Characteristics

| User Class | Role & Persona | Technical Expertise | Primary Interaction |
| :--- | :--- | :--- | :--- |
| **Civic-Tech / App Developer** | Builds WhatsApp bots, voice assistants, or farmer advisory apps requiring live government data. | Intermediate to High (REST APIs, JSON schemas). | Registers target URLs and consumes `GET /api/v1/extract/{id}` endpoints. |
| **Autonomous AI Agent (MCP Client)** | LLM-based assistants (e.g., Claude Desktop, Cursor, LangChain agents) requiring live web context. | Automated / Machine-to-Machine via JSON-RPC. | Discovers and invokes tools via the native MCP server interface. |
| **System Operator / DevOps** | Monitors endpoint health, healing telemetry, and CAPTCHA human-in-the-loop (HITL) alerts. | Intermediate (Web dashboards, basic DOM inspection). | Monitors the Next.js Mission Control UI and resolves session blocks. |

### 2.3 Operating Environment and Platforms
* **Backend Runtime:** Python $3.11+$, `FastAPI`, `Uvicorn` ASGI server.
* **Browser Automation:** `Playwright` (Headless Chromium binary).
* **Validation & Persistence:** `Pydantic v2` for dynamic runtime schema validation; `SQLite 3` for lightweight relational persistence.
* **AI / Multimodal Inference:** `Gemma 4` (via Gemini API) or Open-Weight Vision LLMs (`Qwen2.5-VL` / `Llama-3.2-Vision` / `DeepSeek`) accessed via standard HTTPS REST SDKs.
* **Frontend Environment:** Node.js $20+$, `Next.js` (App Router), `React`, `Tailwind CSS`, compatible with all modern evergreen browsers (Chrome, Firefox, Edge, Safari).
* **OS Compatibility:** Cross-platform (Linux, macOS, Windows WSL2).

### 2.4 Design and Implementation Constraints
* **Time Constraint:** Full MVP must be engineered from an empty repository within a strict $12\text{-hour}$ window.
* **Open-Source Mandate:** All core dependencies, licenses, and model weights/APIs must be explicitly documented in the public repository `README.md`.
* **Context Window Constraint:** Raw legacy government HTML pages frequently exceed $50,000$ tokens. The system must deterministically prune non-semantic DOM nodes before invoking the LLM to prevent context overflow and high latency.

### 2.5 Assumptions and Dependencies
* Target web portals render data within the accessible DOM (Server-Side Rendered or standard Client-Side Hydration) and do not exclusively render text inside encrypted WebGL canvases.
* External network connectivity is available to reach the Vision LLM inference endpoint during a healing event.
* For live stage evaluation, a locally hosted Next.js Mock Portal (`/mock-gov`) will simulate target government portals to guarantee $100\%$ network reliability.

---

## 3. System Features & Functional Requirements

### 3.1 Feature 1: Endpoint Registration & Schema Compiler
* **Priority:** High
* **Description:** Allows a developer to register any target webpage URL along with a plain-English description and a strict key-value JSON schema of the desired output data.
* **User Workflow:**
  1. Developer sends a `POST /api/v1/endpoints/register` payload containing `endpoint_id`, `target_url`, `schema_definition`, and optional `initial_selectors`.
  2. If `initial_selectors` are omitted, MorphAPI triggers an initial discovery pass using the Healing Engine to map the schema fields to CSS selectors.
  3. MorphAPI stores the configuration in SQLite and dynamically compiles a runtime Pydantic model.
* **Inputs:** JSON payload (`endpoint_id: str`, `target_url: HttpUrl`, `schema_spec: dict[str, str]`).
* **Outputs:** `HTTP 201 Created` with the registered endpoint metadata, active selectors, and generated REST/MCP access URLs.
* **Edge Cases:** Invalid URL syntax returns `HTTP 422`; unreachable host during initial discovery marks endpoint status as `DEGRADED`.

### 3.2 Feature 2: Zero-Token Fast Deterministic Extraction Path
* **Priority:** High
* **Description:** Executes rapid data extraction using cached CSS selectors stored in SQLite without calling any AI models.
* **User Workflow:**
  1. Client requests `GET /api/v1/extract/{endpoint_id}`.
  2. FastAPI looks up the active `selectors_json` from SQLite.
  3. Headless Playwright navigates to `target_url` and queries the DOM for each field in the selector map.
  4. Extracted raw text/attributes are passed to the Schema Validation Gate.
* **Inputs:** `endpoint_id` path parameter.
* **Outputs:** Extracted dictionary mapped to the target schema fields, plus execution latency telemetry in milliseconds.
* **Edge Cases:** If a selector matches multiple rows (e.g., a list of Mandi crop prices or GR circulars), the engine extracts an array of structured objects.

### 3.3 Feature 3: Pydantic Runtime Schema Validation & Tripwire
* **Priority:** High
* **Description:** Acts as the deterministic safety gate. Verifies that extracted DOM strings match the expected data types and constraints before returning data to the caller.
* **User Workflow:**
  1. Raw dictionary from Playwright is passed into the dynamically compiled Pydantic model.
  2. Validation checks for missing/empty strings, type mismatches (e.g., extracting a string banner where a float price is expected), and format rules.
  3. If validation passes $\rightarrow$ Return `HTTP 200 OK` immediately.
  4. If Playwright throws a `TimeoutError` OR Pydantic raises a `ValidationError` $\rightarrow$ Trigger the **Multimodal Self-Healing Engine** inside the same HTTP request lifecycle.
* **Inputs:** Unverified dictionary/list extracted by Playwright.
* **Outputs:** Validated JSON payload OR an internal `SelectorBrokenException` signal containing the exact validation failure reason.

### 3.4 Feature 4: Multimodal Self-Healing Engine & DOM AST Pruner
* **Priority:** High
* **Description:** Visually and structurally inspects a mutated webpage when the Fast Path fails, synthesizes new CSS selectors via an open-weight Vision LLM, validates the fix, and hot-patches the SQLite registry.
* **User Workflow:**
  1. Upon receiving `SelectorBrokenException`, Playwright captures a full-viewport `.png` screenshot encoded in Base64.
  2. The **DOM AST Pruner** parses the raw HTML (`BeautifulSoup4`) and strips `<script>`, `<style>`, `<svg>`, `<noscript>`, comments, and long inline styles, compressing token size by $\ge 80\%$.
  3. The system constructs a multimodal prompt containing: (a) Viewport Screenshot, (b) Pruned HTML tree, (c) Target JSON Schema, and (d) The broken selector + error log.
  4. The Vision LLM (`Gemma 4` / `Qwen2.5-VL`) analyzes the visual layout against the pruned DOM and outputs a strict JSON response with the patched CSS selectors and a brief `ai_reasoning` explanation.
  5. MorphAPI re-runs Playwright extraction with the patched selectors and passes the result through the Pydantic Gate.
  6. Once verified, SQLite overwrites `selectors_json`, logs the diff to `healing_logs`, broadcasts a WebSocket event to the dashboard, and returns `HTTP 200 OK` to the waiting client.
* **Inputs:** Base64 PNG screenshot, pruned HTML string, broken selector map, schema specification.
* **Outputs:** Patched selector JSON map, AI reasoning string, and healed data payload (`"healed_this_request": true`).
* **Edge Cases:** If the Vision LLM returns a selector that still fails Pydantic validation, the engine performs $1$ retry with error feedback before returning `HTTP 502 Bad Gateway (Unrecoverable Upstream Mutation)`.

### 3.5 Feature 5: Native Model Context Protocol (MCP) Server Interface
* **Priority:** High
* **Description:** Exposes registered MorphAPI endpoints as standardized MCP tools so any MCP-compliant AI agent can autonomously query legacy portals.
* **User Workflow:**
  1. An MCP Client queries `GET /mcp/tools` (or connects via SSE/Stdio).
  2. MorphAPI dynamically generates tool definitions for every registered endpoint in SQLite (e.g., `fetch_maha_gr_portal`, `fetch_pune_mandi_prices`) along with their input/output schemas.
  3. When the AI agent invokes `POST /mcp/call`, MorphAPI executes the Dual-Path Engine (Fast Path $\rightarrow$ Self-Healing Fallback) and returns the clean JSON result wrapped in the standard MCP response envelope.
* **Inputs:** MCP tool discovery or tool invocation JSON-RPC payload.
* **Outputs:** MCP-compliant `tools/list` and `tools/call` JSON responses.

### 3.6 Feature 6: Mission Control Telemetry UI & Mock Chaos Portal
* **Priority:** Medium (Critical for Live Evaluation Demo)
* **Description:** A dual-screen Next.js interface comprising (1) a live observability dashboard showing fast-path vs. self-healing requests, and (2) a realistic replica of the Maharashtra Mandi / GR portal equipped with a **"Chaos: Redesign UI"** button.
* **User Workflow:**
  1. Presenter opens `/mock-gov` (Version 1: Legacy HTML `<table>` with `.mandi-row` classes) and triggers an extraction from Mission Control (`/`). Dashboard flashes green (`FAST PATH: 140ms`).
  2. Presenter clicks **"Chaos: Redesign UI"** on `/mock-gov`. The page state switches to Version 2: CSS Grid cards with `.modern-agri-card` classes, reordered columns, and an injected emergency notice banner.
  3. Presenter triggers another extraction. Mission Control displays `TRIPWIRE TRIGGERED`, renders the captured screenshot, shows the old selector vs. the new AI-patched selector, and flashes green (`HEALED: 2.8s`).

### 3.7 Feature 7: Basic CAPTCHA OCR & HITL Session Fallback
* **Priority:** Medium
* **Description:** Handles legacy image-to-text CAPTCHAs automatically via Vision LLM OCR and provides a Human-in-the-Loop session cookie cache for behavioral CAPTCHAs.
* **User Workflow:**
  1. If Playwright detects a legacy `<img id="captcha">` blocking the view, it crops the bounding box, passes it to the Vision LLM for alphanumeric OCR, and injects the text.
  2. If an advanced behavioral block occurs, the endpoint status updates to `AUTH_REQUIRED` on Mission Control, allowing an operator to inject a valid session cookie into SQLite.

---

## 4. External Interface Requirements

### 4.1 User Interfaces
* **Mission Control Dashboard (`/`):** Dark-mode command center built with Next.js and Tailwind CSS. Must include:
  * **Live Telemetry Header:** Total requests, Fast-Path hit rate ($\%$), Total auto-heals, Average latency.
  * **Endpoint Registry Cards:** Status badges (`HEALTHY`, `HEALING`, `DEGRADED`), active CSS selector inspector, and a "Test Extract" trigger button.
  * **Visual Healing Audit Feed:** Side-by-side comparison showing the broken selector, the live viewport screenshot captured during failure, the LLM's reasoning trace, and the newly patched selector.
* **Mock Civic Target Portal (`/mock-gov`):** A toggleable web page simulating a Maharashtra Government Resolution / Mandi Price board with at least $2$ completely distinct DOM/CSS structural trees.

### 4.2 Hardware and Software Interfaces
* **Headless Browser Interface:** Interacts with the local OS graphics/headless rendering subsystem via Playwright's async Python API (`playwright.async_api`).
* **Database Interface:** Connects to a local file-based SQLite database (`morphapi.db`) via Python's built-in `sqlite3` or `aiosqlite` driver.

### 4.3 Communications Interfaces
* **REST API Protocol:** HTTP/1.1 and HTTP/2 over TCP, accepting and returning `application/json`. CORS middleware enabled for Next.js frontend communication.
* **MCP Interface:** Standard JSON-RPC $2.0$ formatted endpoints (`/mcp/tools`, `/mcp/call`) for seamless agent harness integration.
* **Real-Time Telemetry:** Polling or WebSocket (`/ws/telemetry`) interface streaming live healing state transitions to the Next.js dashboard.

---

## 5. Non-Functional Requirements (NFRs)

### 5.1 Performance and Latency Targets
* **`NFR-1.1` (Fast Path Latency):** Standard cached extractions against local or low-latency portals must complete in $\le 250\text{ ms}$ (excluding upstream target network TTFB).
* **`NFR-1.2` (Self-Healing Recovery Time):** End-to-end multimodal healing (screenshot capture + DOM pruning + Vision LLM inference + selector re-verification) must complete within $\le 5.0\text{ s}$.
* **`NFR-1.3` (DOM Token Compression):** The DOM AST Pruner must reduce raw HTML character length by $\ge 80\%$ while preserving $100\%$ of visible text nodes and structural `id`/`class` attributes.

### 5.2 Security, Authentication, and Data Privacy
* **`NFR-2.1` (Secret Management):** All LLM API keys (Gemini / DeepSeek / OpenRouter) must be loaded strictly via environment variables (`.env`) and never committed to version control.
* **`NFR-2.2` (Data Sanitization):** Extracted strings must be sanitized of executable `<script>` payloads before being returned to downstream consumers or AI agents.
* **`NFR-2.3` (PII Redaction Compatibility):** Optional regex pre-filtering can mask 12-digit Aadhaar-like patterns or phone numbers in public documents prior to LLM ingestion.

### 5.3 Reliability, Availability, and Recovery Plans
* **`NFR-3.1` (Zero-Downtime Hot-Swapping):** Selector updates in SQLite must take effect immediately on the next incoming request without restarting the FastAPI server.
* **`NFR-3.2` (Idempotent Healing Lock):** If $10$ concurrent requests hit a broken endpoint simultaneously, MorphAPI must acquire an async lock per `endpoint_id` so the Vision LLM healing loop runs only **once**, serving the healed result to all waiting requests.

### 5.4 Scalability and Maintainability
* **`NFR-4.1` (Modular Separation):** The Playwright scraper, DOM pruner, Vision LLM healer, and FastAPI routes must be decoupled into separate Python modules so the underlying LLM can be swapped (e.g., switching between `Gemma 4` and `DeepSeek`) by changing a single configuration variable.

---

## 6. Data Requirements

### 6.1 Database Entities, Core Relationships, and Data Models
MorphAPI utilizes a lightweight relational schema in SQLite comprising two primary tables:

#### Table 1: `endpoints`
Stores registered target portals, expected Pydantic schema definitions, and currently active CSS selectors.

| Column Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `TEXT` | `PRIMARY KEY` | Unique slug identifier (e.g., `maha_gr_portal`, `pune_mandi`). |
| `name` | `TEXT` | `NOT NULL` | Human-readable title of the civic portal. |
| `target_url` | `TEXT` | `NOT NULL` | Full HTTP/HTTPS URL of the target webpage. |
| `schema_json` | `TEXT` | `NOT NULL` | JSON string defining target field names and primitive types. |
| `selectors_json`| `TEXT` | `NOT NULL` | JSON string mapping each schema field to its active CSS selector. |
| `status` | `TEXT` | `DEFAULT 'HEALTHY'` | Current state (`HEALTHY`, `HEALING`, `DEGRADED`). |
| `last_verified` | `DATETIME` | `DEFAULT CURRENT_TIMESTAMP` | Timestamp of the last successful Pydantic-verified extraction. |

#### Table 2: `healing_logs`
Stores an immutable audit trail of every autonomous self-healing event to power the Mission Control UI and Q&A defense.

| Column Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `log_id` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT` | Unique sequential event ID. |
| `endpoint_id` | `TEXT` | `FOREIGN KEY (endpoints.id)` | Reference to the healed endpoint. |
| `timestamp` | `DATETIME` | `DEFAULT CURRENT_TIMESTAMP` | Exact time the UI mutation was detected and healed. |
| `failure_reason`| `TEXT` | `NOT NULL` | Exception or Pydantic validation error that tripped the healer. |
| `old_selectors` | `TEXT` | `NOT NULL` | Snapshot of the broken CSS selector JSON prior to healing. |
| `new_selectors` | `TEXT` | `NOT NULL` | Newly synthesized and verified CSS selector JSON. |
| `ai_reasoning` | `TEXT` | `NOT NULL` | Explanation from the Vision LLM detailing how it relocated the data. |
| `screenshot_b64`| `TEXT` | `NULLABLE` | Base64-encoded PNG viewport snapshot captured at failure time. |
| `heal_latency_ms`| `INTEGER` | `NOT NULL` | Total duration of the self-healing cycle in milliseconds. |

### 6.2 Data Retention and Storage Policies
* **Selector State:** Active configurations in the `endpoints` table persist indefinitely until explicitly deleted via API.
* **Healing Telemetry Retention:** To prevent local SQLite bloat from Base64 screenshots during heavy testing, the system retains the most recent $50$ records in `healing_logs` per endpoint, automatically pruning older visual snapshots while preserving text audit logs.