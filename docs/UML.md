# MorphAPI — System Design & UML Architectural Blueprints

This document contains the complete visual engineering specifications for **MorphAPI**. All diagrams are provided in **Mermaid.js** (which renders natively inside your GitHub `README.md`) alongside **ASCII Architecture Diagrams** for terminal docs and presentation slides.

---

## 1. High-Level System Context & Architecture Diagram (C4 Level 2)

This diagram illustrates how downstream consumers (WhatsApp bots, civic apps, and MCP AI Agents) interact with MorphAPI's Dual-Path Execution Engine.

```mermaid
graph TB
    subgraph Consumers ["Downstream Consumers & AI Agents"]
        REST["Civic App / WhatsApp Bot<br/>(REST JSON Consumer)"]
        Agent["Autonomous AI Agent<br/>(Claude / Cursor / LangChain)"]
        Admin["Developer / Judge<br/>(Browser)"]
    end

    subgraph MorphAPI ["MorphAPI Gateway (FastAPI + Python)"]
        Router["API & MCP Protocol Router<br/>(/api/v1/extract & /mcp/sse)"]
        Registry[("SQLite State &<br/>Selector Vault")]
        Runner["Fast Deterministic Runner<br/>(Playwright Headless)"]
        Validator["Runtime Schema Gate<br/>(Pydantic Dynamic Model)"]
        
        subgraph Healer ["Autonomous Multimodal Self-Healing Engine"]
            Pruner["DOM AST Pruner<br/>(85% Token Reduction)"]
            Snap["Viewport & Bounding-Box<br/>PNG Capturer"]
            VLM["Multimodal Vision Engine<br/>(Gemma 4 / Open-Weight VLM)"]
        end
        
        WS["WebSocket Telemetry Broadcaster"]
    end

    subgraph Targets ["Target Legacy Portals"]
        MockGov["Local Mock Civic Portal<br/>(Maha GR / Mandi Board + Chaos UI)"]
        LiveGov["Live Legacy Portals<br/>(gr.maharashtra.gov.in / MSAMB)"]
    end

    subgraph Dashboard ["Next.js Mission Control UI"]
        Feed["Live Healing Telemetry Feed"]
        Diff["Visual Screenshot & Selector Diff"]
    end

    REST -->|GET /api/v1/data/:id| Router
    Agent -->|MCP Tool Call: extract_legacy_data| Router
    Router <-->|Fetch Cached Selectors| Registry
    Router -->|Execute Fast Path| Runner
    Runner -->|Scrape DOM| MockGov
    Runner -.->|Scrape DOM| LiveGov
    Runner -->|Raw Extracted Dict| Validator

    Validator -->|Valid Schema (0 Tokens, ~150ms)| Router
    Validator -->|ValidationError / Timeout Tripwire| Pruner
    Validator -->|Trigger Visual Capture| Snap

    Pruner -->|Cleaned HTML Tree| VLM
    Snap -->|Base64 Viewport PNG| VLM
    VLM -->|Patched CSS Selectors + Reasoning| Validator
    VLM -->|Hot-Swap Selectors| Registry

    Router -.->|Stream Events| WS
    VLM -.->|Stream Healing Diff| WS
    WS ==>|Real-Time Updates| Feed
    WS ==>|Visual Proof| Diff
    Admin -->|Click 'Chaos: Redesign UI'| MockGov
```

---

## 2. UML Sequence Diagram: Fast Path vs. Self-Healing Loop

This sequence diagram shows the exact runtime lifecycle when a developer or judge clicks the **"Chaos: Redesign UI"** button during the live demo.

```mermaid
sequenceDiagram
    autonumber
    actor Client as AI Agent / REST Client
    participant API as FastAPI Gateway
    participant DB as SQLite Registry
    participant PW as Playwright Runner
    participant Target as Target Civic Portal
    participant VLM as Gemma 4 / Vision LLM
    participant UI as Mission Control UI (WS)

    Note over Client, UI: CASE 1: Normal Operation (Zero-Token Fast Path)
    Client->>API: GET /api/v1/data/pune_mandi
    API->>DB: Get cached selectors & Pydantic schema
    DB-->>API: Returns {"crop": ".mandi-crop", "price": ".rate-val"}
    API->>PW: Extract using cached selectors
    PW->>Target: Load DOM & query selectors
    Target-->>PW: Returns raw strings
    PW-->>API: Validate against Pydantic Schema (PASS)
    API->>UI: WS Event: FAST_PATH_OK (142ms, 0 Tokens)
    API-->>Client: 200 OK (healed: false, data: [...])

    Note over Client, UI: ⚡ JUDGE CLICKS "CHAOS: REDESIGN UI" ON TARGET PORTAL ⚡

    Note over Client, UI: CASE 2: Broken UI -> Autonomous Self-Healing Path
    Client->>API: GET /api/v1/data/pune_mandi (Request Paused, No 500 Error)
    API->>DB: Get cached selectors
    API->>PW: Attempt extraction with ".mandi-crop"
    PW->>Target: Query ".mandi-crop" (Element Missing / Timeout!)
    PW-->>API: Raises SelectorBrokenException / ValidationError
    API->>UI: WS Event: HEALING_TRIGGERED (Selector '.mandi-crop' failed)

    rect rgb(40, 30, 50)
        Note right of API: Multimodal Self-Healing Loop
        API->>PW: Capture Viewport PNG + Prune DOM AST (<script>/<style> stripped)
        PW->>Target: Snapshot screen & HTML tree
        Target-->>PW: PNG + Clean HTML
        PW-->>API: Visual + Structural Context Payload
        API->>VLM: Prompt(Screenshot, Pruned DOM, Target Schema, Old Selector)
        VLM-->>API: JSON: {"crop": "[data-card-title]", "price": ".new-price-badge", "reason": "Table converted to CSS Grid cards"}
    end

    API->>PW: Re-test new selectors on live page
    PW->>Target: Query "[data-card-title]" & ".new-price-badge"
    Target-->>PW: Returns valid data rows
    PW-->>API: Pydantic Schema Validation (PASS!)
    API->>DB: Hot-swap & persist new selectors + Write Audit Log
    API->>UI: WS Event: HEAL_COMPLETE (3.1s, Patched Diff + Screenshot)
    API-->>Client: 200 OK (healed: true, data: [...])
```

---

## 3. UML Activity / State Machine Diagram: Endpoint Lifecycle

This state diagram models how an endpoint transitions between healthy deterministic execution, healing mode, and human-in-the-loop fallback.

```mermaid
stateDiagram-v2
    [*] --> Unregistered
    Unregistered --> Initializing : POST /api/v1/register (URL + Schema)
    Initializing --> Healthy_FastPath : Initial VLM Selector Discovery & Pydantic Check Pass

    state Healthy_FastPath {
        [*] --> Idle
        Idle --> ExecutingPlaywright : Incoming REST / MCP Request
        ExecutingPlaywright --> PydanticGate : DOM Nodes Found
        PydanticGate --> Idle : Schema Valid (Return 200 OK in ~150ms)
    }

    ExecutingPlaywright --> SelfHealing_Mode : Timeout / Selector Not Found
    PydanticGate --> SelfHealing_Mode : Type Mismatch / Empty Payload

    state SelfHealing_Mode {
        [*] --> CaptureContext
        CaptureContext : 1. Capture Viewport PNG
        CaptureContext : 2. Prune HTML AST (Strip noise)
        CaptureContext --> CheckCaptcha
        CheckCaptcha --> VLM_Inference : Standard UI Drift
        CheckCaptcha --> Captcha_Solver : Image/Behavioral Challenge Detected
        VLM_Inference : Send Image + DOM + Schema to Gemma 4 / VLM
        VLM_Inference --> DryRunVerification : Candidate Selectors Returned
    }

    Captcha_Solver --> VLM_Inference : OCR Solved / HITL Session Cookie Cached
    DryRunVerification --> Healthy_FastPath : Pydantic Validation Passes (Update SQLite Cache)
    DryRunVerification --> Degraded_HITL : Retry Limit (2x) Exceeded
    Degraded_HITL --> Healthy_FastPath : Manual Override via Mission Control
```

---

## 4. UML Class Diagram: Backend Modules (`FastAPI` + `Playwright` + `VLM`)

This class diagram gives your teammates a clear blueprint of the exact classes and methods in the Python backend.

```mermaid
classDiagram
    class MorphAPIGateway {
        +FastAPI app
        +WebSocketManager ws_manager
        +register_endpoint(req: EndpointRegisterRequest) EndpointConfig
        +extract_data(endpoint_id: str) ExtractionResponse
        +mcp_list_tools() List~MCPTool~
        +mcp_call_tool(name: str, args: dict) dict
    }

    class SQLiteRegistry {
        +String db_path
        +get_endpoint(endpoint_id: str) EndpointConfig
        +update_selectors(endpoint_id: str, new_selectors: dict) bool
        +log_healing_event(event: HealingLog) int
        +get_telemetry_logs(limit: int) List~HealingLog~
    }

    class DeterministicRunner {
        +Browser playwright_browser
        +extract_with_selectors(url: str, selectors: dict) RawPayload
        +capture_failure_snapshot(page: Page) SnapshotContext
        +prune_dom_ast(raw_html: str) str
    }

    class DynamicSchemaValidator {
        +build_pydantic_model(schema_def: dict) Type~BaseModel~
        +validate_rows(rows: List~dict~, schema_def: dict) ValidationResult
    }

    class MultimodalHealer {
        +String model_name
        +String api_key
        +diagnose_and_patch(snapshot: SnapshotContext, schema: dict, broken_selectors: dict) HealedPatch
        +solve_simple_captcha(image_b64: str) str
    }

    class SnapshotContext {
        +String url
        +String screenshot_b64
        +String pruned_html
        +String error_trace
    }

    class HealedPatch {
        +Dict~str, str~ new_selectors
        +String ai_reasoning
        +Float confidence_score
        +Int latency_ms
    }

    MorphAPIGateway --> SQLiteRegistry : reads/writes state
    MorphAPIGateway --> DeterministicRunner : executes fast path
    MorphAPIGateway --> DynamicSchemaValidator : enforces types
    MorphAPIGateway --> MultimodalHealer : triggers on failure
    DeterministicRunner ..> SnapshotContext : creates on crash
    MultimodalHealer ..> SnapshotContext : consumes
    MultimodalHealer ..> HealedPatch : produces
```

---

## 5. Entity-Relationship Diagram (ERD): SQLite Database

This ERD shows the relational structure stored inside `morphapi.db`.

```mermaid
erDiagram
    ENDPOINTS ||--o{ HEALING_LOGS : "triggers"
    ENDPOINTS ||--o{ REQUEST_TELEMETRY : "records"

    ENDPOINTS {
        string id PK "e.g., maha_gr_portal"
        string name "Maharashtra GR Notice Board"
        string target_url "http://localhost:3000/mock-gov"
        json schema_json "{'title': 'str', 'date': 'str', 'pdf': 'str'}"
        json selectors_json "{'row': 'tr.gr', 'title': '.col-1'}"
        string status "HEALTHY | HEALING | DEGRADED"
        int version "Incremented on every self-heal"
        datetime updated_at
    }

    HEALING_LOGS {
        int id PK
        string endpoint_id FK
        int from_version
        int to_version
        json old_selectors_json
        json new_selectors_json
        string trigger_error "SelectorTimeoutError / ValidationError"
        string ai_reasoning "Table converted to Flexbox cards"
        text screenshot_b64 "Base64 PNG snapshot for UI"
        int heal_duration_ms "e.g., 2840"
        datetime created_at
    }

    REQUEST_TELEMETRY {
        int id PK
        string endpoint_id FK
        string execution_path "FAST_PATH | SELF_HEALED"
        int latency_ms "145 vs 2950"
        int tokens_used "0 vs 1420"
        int http_status "200"
        datetime timestamp
    }
```

---

## 6. Data Flow Diagram (DFD): DOM AST Pruning & Multimodal Context Pipeline

Judges in the **15% Understanding of Implementation** category will ask: *"How do you fit a massive government webpage into the LLM without blowing up token limits or waiting 30 seconds?"* Use this diagram to explain your pipeline.

```text
[ Raw Legacy Webpage (55,000+ Tokens) ]
       │
       ├──► 1. Playwright Viewport Renderer ──────────────────► [ Compressed JPEG/PNG Screenshot ]
       │                                                                       │
       └──► 2. BeautifulSoup4 / lxml AST Parser                                │
               ├── Strip <script>, <style>, <svg>, <noscript>, <meta>          │
               ├── Remove inline style="..." and data-reactid attributes       │
               ├── Collapse empty nested <div> wrappers                        │
               └── Retain structural tags (<table>, <div>, <a>, id, class)     │
                       │                                                       │
                       ▼                                                       ▼
            [ Pruned Structural DOM (~3,200 Tokens) ]              [ Visual Layout Grid ]
                       │                                                       │
                       └───────────────────┬───────────────────────────────────┘
                                           │
                                           ▼
                     ╔═══════════════════════════════════════════╗
                     ║   Gemma 4 / Open-Weight Vision Prompt     ║
                     ║  • System: Strict JSON Selector Compiler  ║
                     ║  • Inputs: Screenshot + Pruned DOM        ║
                     ║  • Target: Pydantic Field Schema          ║
                     ╚═════════════════════╤═════════════════════╝
                                           │
                                           ▼
                     [ Verified CSS Selector Patch (JSON) ]
```