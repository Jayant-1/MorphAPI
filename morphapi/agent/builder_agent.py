"""
MorphAPI Deep Agents Harness
Provides high-level bounded planning, scoped tool use, tool-call budgeting,
deadline enforcement, and evidence management.
"""

import asyncio
import json
import logging
import time
from typing import Any
from pydantic import BaseModel, Field

from morphapi.config import settings
from morphapi.agent.nim_provider import NvidiaNimProvider
from morphapi.agent.tools import AgentToolRegistry
from morphapi.agent.prompts import AGENT_SYSTEM_PROMPT
from morphapi.schemas.contracts import SelectorPatch
from morphapi.schemas.errors import FailureCode, BudgetExhaustedError, NIMProviderError

logger = logging.getLogger("morphapi.deepagents")


class AgentInvestigationResult(BaseModel):
    success: bool
    candidate_patch: SelectorPatch | None = None
    clarification_requested: dict[str, Any] | None = None
    tool_calls_executed: int
    total_latency_ms: int
    error_message: str | None = None
    audit_trace: list[dict[str, Any]] = Field(default_factory=list)


class DeepAgentsHarness:
    """
    Higher-level agent harness implementing bounded planning and scoped tool calling.
    """

    def __init__(
        self,
        provider: NvidiaNimProvider | None = None,
        tool_registry: AgentToolRegistry | None = None,
        max_tool_calls: int | None = None,
        deadline_seconds: float | None = None,
        per_tool_timeout: float | None = None,
    ):
        self.provider = provider or NvidiaNimProvider()
        self.tool_registry = tool_registry or AgentToolRegistry()
        self.max_tool_calls = max_tool_calls if max_tool_calls is not None else settings.workflow_max_tool_calls
        self.deadline_seconds = deadline_seconds if deadline_seconds is not None else settings.workflow_deadline_seconds
        self.per_tool_timeout = per_tool_timeout if per_tool_timeout is not None else settings.per_tool_timeout_seconds

    async def execute_tool(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Executes a tool with per-tool timeout enforcement."""
        tool_fn = getattr(self.tool_registry, tool_name, None)
        if not tool_fn or not callable(tool_fn):
            return {"error": f"Tool '{tool_name}' is not registered or prohibited"}

        try:
            return await asyncio.wait_for(tool_fn(**args), timeout=self.per_tool_timeout)
        except asyncio.TimeoutError:
            return {"error": f"Tool '{tool_name}' timed out after {self.per_tool_timeout}s"}
        except Exception as e:
            return {"error": f"Tool '{tool_name}' failed: {e}"}

    async def investigate_and_propose(
        self,
        target_url: str,
        schema_definition: dict[str, str],
        failure_context: str | None = None,
        previous_selectors: dict[str, str] | None = None,
        scope_id: str | None = None,
    ) -> AgentInvestigationResult:
        """
        Executes bounded planning loop: model calls narrow tools to inspect, test,
        and propose candidate configurations within strict tool-call and deadline budgets.
        """
        start_ts = time.monotonic()
        tool_defs = self.tool_registry.get_tool_definitions()
        tool_call_count = 0
        audit_trace: list[dict[str, Any]] = []

        user_content = (
            f"Target URL: {target_url}\n"
            f"Target Schema: {json.dumps(schema_definition, indent=2)}\n"
        )
        if failure_context:
            user_content += f"Failure Context:\n{failure_context}\n"
        if previous_selectors:
            user_content += f"Previous Selectors:\n{json.dumps(previous_selectors, indent=2)}\n"

        user_content += (
            "\nPlease investigate the page, test candidate selectors, and call "
            "'submit_candidate_configuration' when verified candidates are ready, "
            "or 'request_customer_clarification' if human guidance is needed."
        )

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": AGENT_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

        submitted_patch: SelectorPatch | None = None
        clarification: dict[str, Any] | None = None

        # Bounded loop
        while tool_call_count < self.max_tool_calls:
            # Check overall deadline
            elapsed = time.monotonic() - start_ts
            if elapsed > self.deadline_seconds:
                return AgentInvestigationResult(
                    success=False,
                    tool_calls_executed=tool_call_count,
                    total_latency_ms=int(elapsed * 1000),
                    error_message=f"Workflow deadline of {self.deadline_seconds}s exceeded",
                    audit_trace=audit_trace,
                )

            try:
                completion = await self.provider.create_chat_completion(
                    messages=messages,
                    tools=tool_defs,
                    tool_choice="auto",
                    temperature=0.1,
                )
            except NIMProviderError as npe:
                elapsed = time.monotonic() - start_ts
                return AgentInvestigationResult(
                    success=False,
                    tool_calls_executed=tool_call_count,
                    total_latency_ms=int(elapsed * 1000),
                    error_message=f"Provider error: {npe.message}",
                    audit_trace=audit_trace,
                )

            choice = completion.choices[0]
            msg = choice.message
            tool_calls = getattr(msg, "tool_calls", None)

            if not tool_calls:
                # No more tools called; check if model submitted proposal in text
                content = msg.content or ""
                audit_trace.append({"role": "assistant", "content": content})
                break

            # Process each tool call
            messages.append({
                "role": "assistant",
                "content": msg.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in tool_calls
                ],
            })

            for tc in tool_calls:
                tool_call_count += 1
                fname = tc.function.name
                try:
                    fargs = json.loads(tc.function.arguments)
                except Exception:
                    fargs = {}

                tool_result = await self.execute_tool(fname, fargs)
                audit_trace.append({
                    "tool": fname,
                    "arguments": fargs,
                    "result_summary": str(tool_result)[:300],
                })

                # Check if submission tool was called
                if fname == "submit_candidate_configuration" and tool_result.get("accepted"):
                    submitted_patch = SelectorPatch(
                        new_selectors=tool_result["selector_map"],
                        ai_reasoning=tool_result["rationale"],
                        evidence_refs=tool_result.get("evidence_refs", []),
                        confidence_score=0.9,
                    )
                elif fname == "request_customer_clarification":
                    clarification = tool_result

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(tool_result, default=str),
                })

            if submitted_patch or clarification:
                break

        elapsed_ms = int((time.monotonic() - start_ts) * 1000)

        # If budget exhausted without outcome
        if tool_call_count >= self.max_tool_calls and not submitted_patch and not clarification:
            return AgentInvestigationResult(
                success=False,
                tool_calls_executed=tool_call_count,
                total_latency_ms=elapsed_ms,
                error_message=f"Tool call budget exhausted ({self.max_tool_calls} calls)",
                audit_trace=audit_trace,
            )

        return AgentInvestigationResult(
            success=submitted_patch is not None,
            candidate_patch=submitted_patch,
            clarification_requested=clarification,
            tool_calls_executed=tool_call_count,
            total_latency_ms=elapsed_ms,
            audit_trace=audit_trace,
        )
