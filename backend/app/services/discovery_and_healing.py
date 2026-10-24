"""
MorphAPI Selector Discovery and Self-Healing Engine
Orchestrates AI-powered selector discovery and repair using NVIDIA NIM and LangGraph.
Guarantees:
- Per-endpoint concurrency locking with double-check pattern.
- Strict Pydantic parsing of model proposals.
- Real Playwright live verification before any selector patch is saved.
- Preserves last known verified selectors on failure.
- Bounded retries (max 1 retry with error feedback).
- Emits structured telemetry events.
- Powered by LangGraph state machine with durable checkpointing.
"""

import asyncio
import logging
import os
import time
from typing import Any, Callable, Coroutine
from pydantic import BaseModel

from backend.app.adapters.nvidia_nim import NvidiaNimAdapter
from backend.app.models.contracts import (
    ExtractionResult,
    SelectorPatch,
    TelemetryEvent,
)
from backend.app.services.extraction import PlaywrightExtractionService
from backend.app.services.healing_graph import LangGraphHealingEngine, HealingWorkflowState

logger = logging.getLogger("morphapi.healing")


class HealingResult(BaseModel):
    success: bool
    endpoint_id: str
    selectors: dict[str, str] | None = None
    extraction_result: ExtractionResult | None = None
    patch: SelectorPatch | None = None
    error_message: str | None = None
    healing_duration_ms: int = 0
    attempt_count: int = 0
    vision_used: bool = False
    status: str = "COMPLETED"


class DiscoveryAndHealingEngine:
    """
    Core engine managing selector discovery for new endpoints and self-healing for broken ones.
    Wraps LangGraph state graph with per-endpoint locking and double-check logic.
    """

    def __init__(
        self,
        extraction_service: PlaywrightExtractionService,
        nim_adapter: NvidiaNimAdapter | None = None,
        max_healing_seconds: float | None = None,
    ):
        self.extraction_service = extraction_service
        self.nim_adapter = nim_adapter or NvidiaNimAdapter()
        self.max_healing_seconds = max_healing_seconds or float(
            os.getenv("MAX_HEALING_SECONDS", "15.0")
        )

        # Per-endpoint concurrency locks
        self._endpoint_locks: dict[str, asyncio.Lock] = {}
        self._master_lock = asyncio.Lock()

    async def _get_endpoint_lock(self, endpoint_id: str) -> asyncio.Lock:
        async with self._master_lock:
            if endpoint_id not in self._endpoint_locks:
                self._endpoint_locks[endpoint_id] = asyncio.Lock()
            return self._endpoint_locks[endpoint_id]

    async def discover_initial_selectors(
        self,
        endpoint_id: str,
        target_url: str,
        schema_definition: dict[str, str],
        save_callback: Callable[[str, dict[str, str], str], Coroutine[Any, Any, None]] | None = None,
        event_callback: Callable[[TelemetryEvent], Coroutine[Any, Any, None]] | None = None,
    ) -> HealingResult:
        """
        Runs LangGraph workflow to discover initial CSS/XPath selectors for an endpoint.
        """
        start_time = time.perf_counter()
        logger.info("Initiating LangGraph initial discovery for endpoint='%s'", endpoint_id)

        # Wrap save callback to conform to LangGraph persistence
        async def langgraph_save(eid: str, sels: dict[str, str], rsn: str, ver: int):
            if save_callback:
                await save_callback(eid, sels, rsn)

        graph_engine = LangGraphHealingEngine(
            extraction_service=self.extraction_service,
            nim_adapter=self.nim_adapter,
            save_callback=langgraph_save,
            event_callback=event_callback,
        )

        initial_state: HealingWorkflowState = {
            "endpoint_id": endpoint_id,
            "target_url": target_url,
            "schema_definition": schema_definition,
            "current_selectors": {},
            "candidate_selectors": None,
            "attempt_count": 0,
            "max_attempts": 2,
            "status": "INITIALIZED",
            "workflow_type": "DISCOVERY",
            "is_verified": False,
            "vision_used": False,
            "persisted_version": 1,
        }

        thread_id = f"discovery_{endpoint_id}_{int(time.time())}"
        config = {"configurable": {"thread_id": thread_id}}

        final_state = await graph_engine.graph.ainvoke(initial_state, config=config)

        duration_ms = int((time.perf_counter() - start_time) * 1000)
        is_success = final_state.get("is_verified", False) and final_state.get("status") == "SUCCESS"

        patch = None
        if is_success and final_state.get("candidate_selectors"):
            patch = SelectorPatch(
                new_selectors=final_state["candidate_selectors"],
                ai_reasoning=final_state.get("ai_reasoning", "LangGraph Discovery"),
                confidence_score=final_state.get("confidence_score"),
            )

        extract_res = None
        if final_state.get("extraction_result"):
            extract_res = ExtractionResult(**final_state["extraction_result"])

        return HealingResult(
            success=is_success,
            endpoint_id=endpoint_id,
            selectors=final_state.get("candidate_selectors"),
            extraction_result=extract_res,
            patch=patch,
            error_message=final_state.get("error_context"),
            healing_duration_ms=duration_ms,
            attempt_count=final_state.get("attempt_count", 1),
            vision_used=final_state.get("vision_used", False),
            status=final_state.get("status", "FAILED"),
        )

    async def heal_endpoint(
        self,
        endpoint_id: str,
        target_url: str,
        schema_definition: dict[str, str],
        failing_selectors: dict[str, str],
        initial_failure_reason: str,
        current_version: int = 1,
        get_latest_selectors_fn: Callable[[str], Coroutine[Any, Any, dict[str, str] | None]] | None = None,
        save_callback: Callable[[str, dict[str, str], str, int], Coroutine[Any, Any, None]] | None = None,
        event_callback: Callable[[TelemetryEvent], Coroutine[Any, Any, None]] | None = None,
    ) -> HealingResult:
        """
        Coordinates self-healing for an endpoint with failing selectors via LangGraph.
        Under per-endpoint lock, handles double-check, bounded repair loop, and verification.
        """
        start_time = time.perf_counter()
        lock = await self._get_endpoint_lock(endpoint_id)

        async with lock:
            # 1. Double-check pattern: re-read selectors to see if another concurrent worker healed it
            if get_latest_selectors_fn:
                latest_selectors = await get_latest_selectors_fn(endpoint_id)
                if latest_selectors and latest_selectors != failing_selectors:
                    logger.info("Endpoint '%s' was already healed by another worker. Testing current selectors.", endpoint_id)
                    recheck_res = await self.extraction_service.extract(
                        target_url=target_url,
                        schema_definition=schema_definition,
                        selectors=latest_selectors,
                    )
                    if recheck_res.success and recheck_res.is_schema_valid:
                        return HealingResult(
                            success=True,
                            endpoint_id=endpoint_id,
                            selectors=latest_selectors,
                            extraction_result=recheck_res,
                            healing_duration_ms=int((time.perf_counter() - start_time) * 1000),
                            attempt_count=0,
                            status="ALREADY_HEALED",
                        )

            if event_callback:
                await event_callback(
                    TelemetryEvent(
                        event_type="HEALING_TRIGGERED",
                        endpoint_id=endpoint_id,
                        message=f"Healing triggered: {initial_failure_reason}",
                    )
                )

            graph_engine = LangGraphHealingEngine(
                extraction_service=self.extraction_service,
                nim_adapter=self.nim_adapter,
                save_callback=save_callback,
                event_callback=event_callback,
            )

            initial_state: HealingWorkflowState = {
                "endpoint_id": endpoint_id,
                "target_url": target_url,
                "schema_definition": schema_definition,
                "current_selectors": failing_selectors,
                "candidate_selectors": None,
                "attempt_count": 0,
                "max_attempts": 2,
                "status": "INITIALIZED",
                "workflow_type": "HEALING",
                "error_context": initial_failure_reason,
                "is_verified": False,
                "vision_used": False,
                "persisted_version": current_version,
            }

            thread_id = f"healing_{endpoint_id}_{int(time.time())}"
            config = {"configurable": {"thread_id": thread_id}}

            final_state = await graph_engine.graph.ainvoke(initial_state, config=config)

            duration_ms = int((time.perf_counter() - start_time) * 1000)
            is_success = final_state.get("is_verified", False) and final_state.get("status") == "SUCCESS"

            patch = None
            if is_success and final_state.get("candidate_selectors"):
                patch = SelectorPatch(
                    new_selectors=final_state["candidate_selectors"],
                    ai_reasoning=final_state.get("ai_reasoning", "LangGraph Healing"),
                    confidence_score=final_state.get("confidence_score"),
                )

            extract_res = None
            if final_state.get("extraction_result"):
                extract_res = ExtractionResult(**final_state["extraction_result"])

            return HealingResult(
                success=is_success,
                endpoint_id=endpoint_id,
                selectors=final_state.get("candidate_selectors") if is_success else failing_selectors,
                extraction_result=extract_res,
                patch=patch,
                error_message=final_state.get("error_context"),
                healing_duration_ms=duration_ms,
                attempt_count=final_state.get("attempt_count", 1),
                vision_used=final_state.get("vision_used", False),
                status=final_state.get("status", "FAILED"),
            )
