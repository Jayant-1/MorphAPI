"""
MorphAPI Healing Service
Coordinates bounded self-healing and selector discovery jobs using the LangGraph engine.
Applies endpoint-level concurrency locking and double-check verification.
"""

import asyncio
import logging
from typing import Any
from morphapi.workflows.graph import MorphApiHealingGraph
from morphapi.schemas.errors import FailureCode, MorphApiError

logger = logging.getLogger("morphapi.healing_service")


class HealingService:
    """
    Coordinates agentic healing workflows with concurrency control.
    """

    def __init__(self, healing_graph: MorphApiHealingGraph | None = None):
        self.healing_graph = healing_graph or MorphApiHealingGraph()
        self._endpoint_locks: dict[str, asyncio.Lock] = {}
        self._master_lock = asyncio.Lock()

    async def _get_endpoint_lock(self, endpoint_id: str) -> asyncio.Lock:
        async with self._master_lock:
            if endpoint_id not in self._endpoint_locks:
                self._endpoint_locks[endpoint_id] = asyncio.Lock()
            return self._endpoint_locks[endpoint_id]

    async def heal_endpoint(
        self,
        endpoint_id: str,
        target_url: str,
        schema_definition: dict[str, str],
        current_selectors: dict[str, str],
        current_version: int = 1,
        failure_reason: str = "Selector failure",
    ) -> dict[str, Any]:
        """
        Runs bounded self-healing workflow under an endpoint-level lock.
        """
        lock = await self._get_endpoint_lock(endpoint_id)
        async with lock:
            thread_id = f"heal_{endpoint_id}_{current_version}"
            initial_state = {
                "endpoint_id": endpoint_id,
                "workflow_id": thread_id,
                "target_url": target_url,
                "schema_definition": schema_definition,
                "active_selectors": current_selectors,
                "version_promoted": current_version,
                "error_context": failure_reason,
            }

            config = {"configurable": {"thread_id": thread_id}}
            logger.info("[%s] Starting LangGraph healing workflow (thread=%s)", endpoint_id, thread_id)

            final_state = await self.healing_graph.graph.ainvoke(initial_state, config=config)

            if not final_state.get("is_verified") or final_state.get("status") == "FAILED":
                err = final_state.get("error_context") or "Self-healing could not discover valid selectors"
                logger.error("[%s] Self-healing workflow failed: %s", endpoint_id, err)
                raise MorphApiError(
                    code=FailureCode.WORKFLOW_FAILED,
                    message=f"Endpoint healing failed: {err}",
                    details={"endpoint_id": endpoint_id, "status": "DEGRADED"},
                )

            return {
                "status": "HEALTHY",
                "version": final_state.get("version_promoted"),
                "new_selectors": final_state.get("active_selectors"),
                "data": final_state.get("sample_data"),
            }
