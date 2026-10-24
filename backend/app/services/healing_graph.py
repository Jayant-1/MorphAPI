"""
MorphAPI LangGraph Orchestration for Selector Discovery and Self-Healing
Implements agentic workflow for website inspection, proposal, bounded repair loops,
deterministic verification routing, and human-in-the-loop approval.
"""

import asyncio
import logging
import time
from typing import Any, Callable, Coroutine, Literal, TypedDict
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from backend.app.adapters.nvidia_nim import NvidiaNimAdapter, CandidateSelectorsResponse
from backend.app.models.contracts import SelectorPatch, TelemetryEvent
from backend.app.services.extraction import PlaywrightExtractionService

logger = logging.getLogger("morphapi.langgraph")


class HealingWorkflowState(TypedDict, total=False):
    """
    Durable state schema for LangGraph agentic discovery and self-healing.
    """
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


class LangGraphHealingEngine:
    """
    LangGraph-based state machine orchestrating inspection, NIM proposal,
    bounded repair attempts, verification routing, and persistence.
    """

    def __init__(
        self,
        extraction_service: PlaywrightExtractionService,
        nim_adapter: NvidiaNimAdapter | None = None,
        checkpointer: Any | None = None,
        save_callback: Callable[[str, dict[str, str], str, int], Coroutine[Any, Any, None]] | None = None,
        event_callback: Callable[[TelemetryEvent], Coroutine[Any, Any, None]] | None = None,
    ):
        self.extraction_service = extraction_service
        self.nim_adapter = nim_adapter or NvidiaNimAdapter()
        self.checkpointer = checkpointer or MemorySaver()
        self.save_callback = save_callback
        self.event_callback = event_callback
        self.graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(HealingWorkflowState)

        # 1. Add nodes
        builder.add_node("inspect_page", self._inspect_page_node)
        builder.add_node("propose_selectors", self._propose_selectors_node)
        builder.add_node("validate_candidates", self._validate_candidates_node)
        builder.add_node("persist_patch", self._persist_patch_node)
        builder.add_node("human_approval", self._human_approval_node)
        builder.add_node("mark_failed", self._mark_failed_node)

        # 2. Add edges
        builder.set_entry_point("inspect_page")
        builder.add_edge("inspect_page", "propose_selectors")
        builder.add_edge("propose_selectors", "validate_candidates")

        # 3. Conditional routing after validation
        builder.add_conditional_edges(
            "validate_candidates",
            self._route_validation_result,
            {
                "persist": "persist_patch",
                "retry": "propose_selectors",
                "needs_approval": "human_approval",
                "fail": "mark_failed",
            },
        )

        builder.add_edge("persist_patch", END)
        builder.add_edge("human_approval", END)
        builder.add_edge("mark_failed", END)

        return builder.compile(checkpointer=self.checkpointer)

    async def _emit_telemetry(self, event_type: str, state: HealingWorkflowState, message: str, details: dict | None = None):
        if self.event_callback:
            try:
                await self.event_callback(
                    TelemetryEvent(
                        event_type=event_type,
                        endpoint_id=state.get("endpoint_id", "unknown"),
                        message=message,
                        details=details or {},
                    )
                )
            except Exception as e:
                logger.warning("Failed to emit telemetry: %s", e)

    async def _inspect_page_node(self, state: HealingWorkflowState) -> dict[str, Any]:
        """Node 1: Inspects website DOM and captures screenshot."""
        endpoint_id = state["endpoint_id"]
        target_url = state["target_url"]
        logger.info("[%s] LangGraph Node: inspect_page", endpoint_id)

        await self._emit_telemetry("HEALING_CONTEXT_CAPTURED", state, "Inspecting live page DOM and screenshot")

        # Call Playwright to inspect page
        browser = await self.extraction_service._get_browser()
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()

        try:
            await page.goto(target_url, timeout=self.extraction_service.timeout_ms, wait_until="domcontentloaded")
            title = await page.title()
            full_html = await page.content()
            from backend.app.services.dom_pruner import prune_dom
            pruned = prune_dom(full_html)
            screenshot_bytes = await page.screenshot(type="png")
            import base64
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode("ascii")

            return {
                "page_title": title,
                "pruned_dom": pruned,
                "screenshot_b64": screenshot_b64,
                "status": "INSPECTING",
            }
        except Exception as e:
            return {
                "page_title": None,
                "pruned_dom": "",
                "screenshot_b64": None,
                "error_context": f"Page inspection error: {e}",
                "status": "FAILED",
            }
        finally:
            await context.close()

    async def _propose_selectors_node(self, state: HealingWorkflowState) -> dict[str, Any]:
        """Node 2: Queries NVIDIA NIM for candidate selectors."""
        endpoint_id = state["endpoint_id"]
        attempt = state.get("attempt_count", 0) + 1
        logger.info("[%s] LangGraph Node: propose_selectors (attempt %d/%d)", endpoint_id, attempt, state.get("max_attempts", 2))

        await self._emit_telemetry(
            "HEALING_PATCH_PROPOSED",
            state,
            f"Querying NVIDIA NIM for selectors (attempt {attempt})",
        )

        try:
            resp: CandidateSelectorsResponse = await self.nim_adapter.propose_selectors(
                target_url=state["target_url"],
                page_title=state.get("page_title"),
                schema_definition=state["schema_definition"],
                pruned_dom=state.get("pruned_dom", ""),
                screenshot_b64=state.get("screenshot_b64"),
                previous_selectors=state.get("current_selectors"),
                error_context=state.get("error_context"),
            )
            return {
                "candidate_selectors": resp.new_selectors,
                "ai_reasoning": resp.ai_reasoning,
                "confidence_score": resp.confidence_score,
                "vision_used": resp.vision_enabled,
                "attempt_count": attempt,
                "status": "PROPOSING",
            }
        except Exception as e:
            logger.error("[%s] Error proposing selectors: %s", endpoint_id, e)
            return {
                "attempt_count": attempt,
                "error_context": f"NIM proposal failed: {e}",
                "status": "PROPOSING",
            }

    async def _validate_candidates_node(self, state: HealingWorkflowState) -> dict[str, Any]:
        """Node 3: Deterministically validates candidate selectors on live page using Playwright."""
        endpoint_id = state["endpoint_id"]
        candidates = state.get("candidate_selectors")
        logger.info("[%s] LangGraph Node: validate_candidates", endpoint_id)

        if not candidates:
            return {
                "is_verified": False,
                "error_context": "No candidate selectors provided by model",
                "status": "VALIDATING",
            }

        extract_result = await self.extraction_service.extract(
            target_url=state["target_url"],
            schema_definition=state["schema_definition"],
            selectors=candidates,
        )

        is_verified = extract_result.success and extract_result.is_schema_valid
        return {
            "extraction_result": extract_result.model_dump(),
            "is_verified": is_verified,
            "error_context": extract_result.error_message if not is_verified else None,
            "status": "VALIDATING",
        }

    def _route_validation_result(self, state: HealingWorkflowState) -> Literal["persist", "retry", "needs_approval", "fail"]:
        """Router: Decides whether to persist, retry bounded loop, request approval, or fail."""
        if state.get("is_verified", False):
            return "persist"

        attempts = state.get("attempt_count", 0)
        max_attempts = state.get("max_attempts", 2)

        if attempts < max_attempts:
            logger.info("Validation failed, bounded retry available (%d/%d)", attempts, max_attempts)
            return "retry"

        # Check for ambiguity requiring operator approval
        err = state.get("error_context", "") or ""
        if "ambiguous" in err.lower() or "multiple" in err.lower():
            return "needs_approval"

        return "fail"

    async def _persist_patch_node(self, state: HealingWorkflowState) -> dict[str, Any]:
        """Node 4: Transactionally persists the verified selectors."""
        endpoint_id = state["endpoint_id"]
        new_selectors = state["candidate_selectors"] or {}
        reasoning = state.get("ai_reasoning", "Verified by LangGraph pipeline")
        logger.info("[%s] LangGraph Node: persist_patch (VERIFIED)", endpoint_id)

        if self.save_callback:
            await self.save_callback(endpoint_id, new_selectors, reasoning, state.get("persisted_version", 1) + 1)

        await self._emit_telemetry(
            "HEAL_COMPLETE",
            state,
            "Candidate patch verified deterministically and persisted",
            details={"selectors": new_selectors},
        )

        return {
            "current_selectors": new_selectors,
            "status": "SUCCESS",
            "is_verified": True,
        }

    async def _human_approval_node(self, state: HealingWorkflowState) -> dict[str, Any]:
        """Node 5: Routes ambiguous selector conflicts for human / operator approval."""
        endpoint_id = state["endpoint_id"]
        logger.warning("[%s] LangGraph Node: human_approval required due to ambiguous match", endpoint_id)

        await self._emit_telemetry(
            "ENDPOINT_STATUS_CHANGED",
            state,
            "Selector ambiguity requires operator approval",
            details={"error": state.get("error_context")},
        )

        return {
            "status": "NEEDS_APPROVAL",
            "is_verified": False,
        }

    async def _mark_failed_node(self, state: HealingWorkflowState) -> dict[str, Any]:
        """Node 6: Final failure node. Preserves previous verified selectors."""
        endpoint_id = state["endpoint_id"]
        logger.error("[%s] LangGraph Node: mark_failed after bounded retries", endpoint_id)

        await self._emit_telemetry(
            "HEALING_FAILED",
            state,
            f"Workflow failed: {state.get('error_context')}",
        )

        return {
            "status": "FAILED",
            "is_verified": False,
        }
