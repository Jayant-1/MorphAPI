"""
MorphAPI Workflow Policies & Budget Guardrails
Defines hard limits on attempts, tool calls, wall-clock time, and candidate proposals.
"""

import time
from typing import NamedTuple

from morphapi.config import settings
from morphapi.workflows.state import WorkflowState


class WorkflowBudget(NamedTuple):
    max_attempts: int
    max_tool_calls: int
    deadline_seconds: float
    per_tool_timeout: float


def get_default_budget() -> WorkflowBudget:
    return WorkflowBudget(
        max_attempts=settings.workflow_max_attempts,
        max_tool_calls=settings.workflow_max_tool_calls,
        deadline_seconds=settings.workflow_deadline_seconds,
        per_tool_timeout=settings.per_tool_timeout_seconds,
    )


def is_budget_exhausted(state: WorkflowState) -> tuple[bool, str | None]:
    """
    Checks if any bounded budget limit has been reached.
    """
    # 1. Check attempt count
    attempts = state.get("attempt_count", 0)
    max_attempts = state.get("max_attempts", settings.workflow_max_attempts)
    if attempts >= max_attempts:
        return True, f"Maximum attempt budget exhausted ({attempts}/{max_attempts})"

    # 2. Check tool-call budget
    tool_calls = state.get("tool_call_count", 0)
    max_tool_calls = state.get("max_tool_calls", settings.workflow_max_tool_calls)
    if tool_calls >= max_tool_calls:
        return True, f"Tool-call budget exhausted ({tool_calls}/{max_tool_calls})"

    # 3. Check wall-clock deadline
    deadline = state.get("deadline_ts")
    if deadline and time.monotonic() > deadline:
        return True, "Overall workflow wall-clock deadline exceeded"

    return False, None
