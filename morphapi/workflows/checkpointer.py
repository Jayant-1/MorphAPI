"""
MorphAPI Durable Workflow Checkpointer & Idempotency Controls
Manages workflow state snapshots, resume operations, and prevents duplicate side effects.
Workflow checkpoints are kept strictly isolated from the authoritative business database.
"""

import logging
from typing import Any
from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger("morphapi.checkpointer")


class WorkflowCheckpointer:
    """
    Manages persistent graph checkpoints and tracks executed side effects to guarantee idempotency.
    """

    def __init__(self, saver: Any | None = None):
        self.saver = saver or MemorySaver()
        self._executed_promotions: set[str] = set()

    def get_saver(self) -> Any:
        return self.saver

    def mark_promotion_executed(self, workflow_id: str, version: int) -> bool:
        """
        Records that a promotion side-effect was performed for this workflow_id.
        Returns True if this is the first execution (safe to proceed);
        Returns False if already executed (skip to prevent duplicate side effect).
        """
        key = f"{workflow_id}:{version}"
        if key in self._executed_promotions or any(k.startswith(f"{workflow_id}:") for k in self._executed_promotions):
            logger.warning("Duplicate promotion side-effect prevented for '%s'", key)
            return False
        self._executed_promotions.add(key)
        return True

    def is_promotion_executed(self, workflow_id: str, version: int) -> bool:
        key = f"{workflow_id}:{version}"
        return key in self._executed_promotions
