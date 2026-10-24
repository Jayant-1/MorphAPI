# MorphAPI Extraction & Self-Healing Engine (Person 2)

## 1. Overview and Architecture

The Extraction & Self-Healing engine delivers robust, deterministic, AI-assisted web scraping for MorphAPI. It strictly separates:
- **Fast Path:** Real Playwright browser automation with deterministic normalization and Pydantic schema validation. Never calls LLM or LangGraph on success.
- **Agentic Recovery (Slow Path):** LangGraph state machine orchestrating website inspection, NVIDIA NIM / DeepSeek multimodal locator proposal, live candidate verification, bounded retries, and transactional persistence.

```
+-------------------------------------------------------------+
| REST / MCP Request (Person 1 / Person 3)                    |
+-------------------------------------------------------------+
                              |
                              v
       +---------------------------------------------+
       | Fast Path: PlaywrightExtractionService       |
       | - SSRF & Destination Revalidation           |
       | - Explicit Element Conditions                |
       | - Deterministic Normalization                |
       | - Schema Validation                          |
       +---------------------------------------------+
               |                             |
          [Success]                      [Failure]
               |                             |
               v                             v
       ExtractionResponse        +-----------------------+
        (FAST_PATH, <=250ms)     | Per-Endpoint Lock     |
                                 | Double-Check Pattern  |
                                 +-----------------------+
                                             |
                                             v
                     +-----------------------------------------------+
                     | LangGraph Healing & Discovery State Machine   |
                     |  1. inspect_page (DOM + Screenshot)           |
                     |  2. propose_selectors (NVIDIA NIM)            |
                     |  3. validate_candidates (Playwright & Schema) |
                     |  4. route_validation:                         |
                     |       - Pass -> persist_patch (Atomic DB)     |
                     |       - Fail -> Bounded Retry (Max 1)         |
                     |       - Ambiguity -> human_approval           |
                     |       - Exhausted -> mark_failed              |
                     +-----------------------------------------------+
```

---

## 2. Component Interfaces

### 2.1 PlaywrightExtractionService (`backend/app/services/extraction.py`)

Accepts:
- `target_url: str`
- `schema_definition: dict[str, str]` (e.g. `{"crop": "str", "price": "float"}`)
- `selectors: dict[str, str]` (CSS or XPath locators)
- `request_context: dict[str, Any] | None`

Guarantees:
- **SSRF Hardening:** Validates target IP and DNS against private, loopback, link-local, and cloud metadata ranges. Revalidates all navigation and redirect requests at runtime.
- **Explicit Waits:** Waits for `domcontentloaded` and target selector attachment rather than arbitrary sleeps.
- **No Hallucinations:** Never substitutes or fabricates missing values.
- **Diagnostics:** Returns execution path, exact timing (`latency_ms`), per-field selector match counts, and typed failure reasons.

### 2.2 NVIDIA NIM Adapter (`backend/app/adapters/nvidia_nim.py`)

Dedicated adapter connecting to NVIDIA NIM endpoints (hosted or self-hosted).

Configured via environment variables:
- `NVIDIA_NIM_BASE_URL` (default: `https://integrate.api.nvidia.com/v1`)
- `NVIDIA_NIM_API_KEY` (no secrets stored in code)
- `NVIDIA_NIM_MODEL` (e.g., `meta/llama-3.2-11b-vision-instruct`, `deepseek-ai/deepseek-r1`)
- `NVIDIA_NIM_TIMEOUT_SECONDS` (default: 30.0s)
- `NVIDIA_NIM_MAX_RETRIES` (default: 1)

Features:
- **Defensive Prompting:** Encloses DOM in untrusted markers; instructs model to ignore prompt injections embedded inside web pages.
- **Multimodal Support:** Detects model vision capability. If supported, attaches base64 screenshot; otherwise falls back gracefully to DOM-only analysis.
- **Strict Parsing:** Validates output against `CandidateSelectorsResponse` Pydantic model. Rejects dangerous script executions, unknown fields, or empty selectors.

### 2.3 LangGraph Healing State Machine (`backend/app/services/healing_graph.py`)

State Schema:
```python
class HealingWorkflowState(TypedDict, total=False):
    endpoint_id: str
    target_url: str
    schema_definition: dict[str, str]
    current_selectors: dict[str, str]
    candidate_selectors: dict[str, str] | None
    ai_reasoning: str | None
    confidence_score: float | None
    pruned_dom: str | None
    screenshot_b64: str | None
    page_title: str | None
    extraction_result: dict[str, Any] | None
    attempt_count: int
    max_attempts: int
    status: Literal["INITIALIZED", "INSPECTING", "PROPOSING", "VALIDATING", "SUCCESS", "FAILED", "NEEDS_APPROVAL"]
    workflow_type: Literal["DISCOVERY", "HEALING"]
    error_context: str | None
    is_verified: bool
    vision_used: bool
    persisted_version: int | None
    telemetry_logs: list[dict[str, Any]]
```

Workflow Nodes:
1. `inspect_page`: Playwright navigates to page, extracts title, pruned DOM (`prune_dom`), and screenshot.
2. `propose_selectors`: Calls NVIDIA NIM adapter for candidate locators.
3. `validate_candidates`: Runs Playwright extraction with candidate selectors and deterministic normalization.
4. `route_validation`: Routes to `persist_patch` on 100% success, loops back for bounded retry on failure, routes to `human_approval` if element counts are ambiguous, or exits to `mark_failed`.
5. `persist_patch`: Executes transactional DB callback and emits `HEAL_COMPLETE`.
6. `mark_failed`: Preserves old selectors, marks status `FAILED`, and returns structured error.

---

## 3. Concurrency, Locking, and Double-Check Pattern

To prevent race conditions and concurrent write hazards:
- Every endpoint has a dedicated async lock (`_endpoint_locks[endpoint_id]`).
- When extraction fails, the worker acquires the endpoint lock.
- **Double-check pattern:** Once the lock is acquired, the engine re-fetches latest stored selectors. If another concurrent worker already healed the endpoint, it tests the updated selectors on fast path and skips running a redundant healing workflow.

---

## 4. Telemetry Events Emitted
- `EXTRACTION_STARTED`
- `FAST_PATH_OK`
- `HEALING_TRIGGERED`
- `HEALING_CONTEXT_CAPTURED`
- `HEALING_PATCH_PROPOSED`
- `HEAL_COMPLETE`
- `HEALING_FAILED`
- `ENDPOINT_STATUS_CHANGED`
