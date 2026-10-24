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

    async def synthesize_from_prompt(
        self,
        prompt: str,
        target_url: str,
        name: str | None = None,
    ) -> dict[str, Any]:
        """
        Agentic synthesis: ReAct Loop (Thought -> Action -> Observation -> Reflection).
        Analyzes user prompt and rendered website to discover schema and candidate selectors,
        verifying each candidate live in Chromium and self-correcting any selector failures.
        """
        import re
        from bs4 import BeautifulSoup

        logger.info("================================================================================")
        logger.info("[Deep Agent ReAct] [START] Initiating Agentic ReAct synthesis for prompt: '%s'", prompt)
        logger.info("[Deep Agent ReAct] [TARGET] URL: %s", target_url)

        # -------------------------------------------------------------
        # Action 1: Scoped Browser Inspection (Tool: inspect_website)
        # -------------------------------------------------------------
        # Resolve any template placeholders for live inspection/testing in Chromium
        inspection_url = target_url
        if "{" in target_url and "}" in target_url:
            from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
            parsed = urlparse(target_url)
            if "{" in parsed.query:
                # For query parameter templates (e.g. ?batch={batch}), strip template filters to load base listing
                qs = parse_qs(parsed.query)
                clean_qs = {k: [v for v in vals if "{" not in v] for k, vals in qs.items()}
                clean_qs = {k: v for k, v in clean_qs.items() if v}
                new_q = urlencode(clean_qs, doseq=True)
                inspection_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_q, parsed.fragment))
            else:
                inspection_url = re.sub(r"\{[a-zA-Z0-9_]+\}", "2025", target_url)
            logger.info("[Deep Agent ReAct] Template target URL '%s' resolved to sample inspection URL '%s'", target_url, inspection_url)

        logger.info("[Deep Agent ReAct] [STAGE 1: INSPECTION] Invoking tool: inspect_website(url='%s')", inspection_url)
        inspect_res = await self.execute_tool("inspect_website", {"url": inspection_url})
        if inspect_res.get("error"):
            logger.warning("[Deep Agent ReAct] [WARN] inspect_website reported error: %s", inspect_res["error"])

        evidence_ref = inspect_res.get("evidence_ref", "")
        page_title = inspect_res.get("page_title", "")
        pruned_dom = inspect_res.get("pruned_dom_sample", "")
        logger.info("[Deep Agent ReAct] [STAGE 1 SUCCESS] Rendered Page Title: '%s' | Extracted DOM: %d characters", page_title, len(pruned_dom))

        discovered_name = name
        discovered_inputs: dict[str, Any] = {}
        discovered_url = target_url
        schema_def: dict[str, str] = {}
        candidate_selectors: dict[str, str] = {}
        rationale = "Candidate selectors discovered and verified through ReAct browser testing"

        # Extract focused DOM sample for the model
        soup_page = BeautifulSoup(pruned_dom, "html.parser")
        main_content = soup_page.find(["main", "article"]) or soup_page.find(id="content") or soup_page.find("body") or soup_page
        dom_sample = str(main_content)[:35000]

        # -------------------------------------------------------------
        # ReAct Loop: Thought -> Action -> Observation -> Reflection
        # -------------------------------------------------------------
        max_turns = 3
        turn = 0
        is_verified = False
        audit_history: list[dict[str, Any]] = []

        system_msg = (
            "You are an expert API Architect and browser automation engineer for MorphAPI. "
            "Keep internal reasoning brief and concise. Focus directly on outputting the valid JSON API contract. "
            "Analyze the user request and rendered DOM to dynamically design the full API contract. "
            "Decide the optimal API inputs, outputs, URL query/path parameter mapping, and CSS selectors. "
            "Identify repeating records, cards, or listing items on the page that correspond to the data requested by the user. "
            "Extract only the main data items (e.g. startup companies, articles, products, rows), NOT website navigation menus, footer links, or search filters. "
            "Return ONLY valid JSON with keys:\n"
            "  \"name\": string display name or slug for the API,\n"
            "  \"inputs\": dictionary of input parameters that users can supply to customize queries (e.g. {\"batch\": {\"type\": \"str\", \"description\": \"Batch filter\", \"default\": \"\"}}),\n"
            "  \"target_url_template\": target URL with placeholders like {param_name} if inputs customize the URL, or the base URL,\n"
            "  \"schema_definition\": dictionary of output field name to type (\"str\", \"int\", \"float\", \"bool\"),\n"
            "  \"selectors\": dictionary of output field name to valid CSS selector matching each record's field,\n"
            "  \"rationale\": string explanation of why these selectors match the target items."
        )

        conversation_messages: list[dict[str, str]] = [
            {"role": "system", "content": system_msg},
            {
                "role": "user",
                "content": (
                    f"User Request: {prompt}\n"
                    f"Target URL: {target_url}\n"
                    f"Page Title: {page_title}\n"
                    f"Rendered Semantic DOM:\n{dom_sample}\n"
                ),
            },
        ]

        while turn < max_turns and not is_verified:
            turn += 1
            logger.info("[Deep Agent ReAct] [TURN %d/%d] [THOUGHT] Reasoning over page layout and field requirements...", turn, max_turns)

            # Stage 2: Ask Model for Proposal (or Correction)
            nim_turn_success = False
            try:
                logger.info("[Deep Agent ReAct] [TURN %d] [LLM CALL] Querying NVIDIA NIM model: %s", turn, self.provider.model_id)
                completion = await self.provider.create_chat_completion(
                    messages=conversation_messages,
                    temperature=0.1,
                    max_tokens=4096,
                )
                msg = completion.choices[0].message
                raw_text = msg.content or getattr(msg, "reasoning_content", "") or ""
                logger.info("[Deep Agent ReAct] [TURN %d] [MODEL RESPONSE] Received (%d chars)", turn, len(raw_text))

                parsed = self.provider._extract_json(raw_text)
                if isinstance(parsed, dict) and "selectors" in parsed and "schema_definition" in parsed:
                    discovered_name = discovered_name or parsed.get("name")
                    discovered_inputs = parsed.get("inputs", {})
                    discovered_url = parsed.get("target_url_template") or target_url
                    schema_def = parsed["schema_definition"]
                    candidate_selectors = parsed["selectors"]
                    rationale = parsed.get("rationale", rationale)
                    nim_turn_success = True
                    logger.info("[Deep Agent ReAct] [TURN %d] Model proposed schema: %s", turn, schema_def)
                    logger.info("[Deep Agent ReAct] [TURN %d] Model proposed selectors: %s", turn, candidate_selectors)

                    # Append assistant message to conversation history
                    conversation_messages.append({"role": "assistant", "content": raw_text})
            except Exception as nim_err:
                logger.warning("[Deep Agent ReAct] [TURN %d] NIM call encountered: %s", turn, nim_err)

            # If NIM was unable to produce valid selectors on this turn, let the ReAct loop continue to the next turn
            if not nim_turn_success:
                logger.warning("[Deep Agent ReAct] [TURN %d] Model did not propose a valid schema/selector dictionary. Continuing ReAct iteration...", turn)
                if turn < max_turns:
                    conversation_messages.append({
                        "role": "user",
                        "content": (
                            "Please review the rendered DOM structure carefully. "
                            "Output ONLY a valid JSON object with keys: 'name', 'inputs', 'target_url_template', "
                            "'schema_definition', 'selectors', and 'rationale'. Do not include conversational markdown before or after the JSON."
                        ),
                    })
                continue

            if not candidate_selectors:
                logger.warning("[Deep Agent ReAct] [TURN %d] No candidate selectors generated.", turn)
                continue

            # Stage 3: Action: Live Selector Testing in Chromium (Tool: test_selectors)
            logger.info("[Deep Agent ReAct] [TURN %d] [ACTION: TEST] Testing candidate selectors live in Chromium...", turn)
            test_res = await self.execute_tool("test_selectors", {"page_ref": inspection_url, "candidates": candidate_selectors})
            evidences = test_res.get("field_evidences", [])
            match_summary = {fe["field_name"]: fe.get("matched_count", 0) for fe in evidences if "field_name" in fe}
            logger.info("[Deep Agent ReAct] [TURN %d] [OBSERVATION] Live DOM match counts: %s", turn, match_summary)

            audit_history.append({
                "turn": turn,
                "selectors": dict(candidate_selectors),
                "match_summary": match_summary,
            })

            # Stage 4: Reflection & Self-Correction Evaluation
            failing_fields = [f for f in candidate_selectors.keys() if match_summary.get(f, 0) == 0]
            error_details = []
            for ev in evidences:
                if ev.get("error"):
                    error_details.append(f"Field '{ev['field_name']}': {ev['error']}")
                    if ev.get("field_name") not in failing_fields:
                        failing_fields.append(ev.get("field_name"))
                elif ev.get("matched_count", 0) == 0:
                    error_details.append(f"Field '{ev['field_name']}' matched 0 elements with selector '{ev.get('selector')}'")

            if not failing_fields and candidate_selectors and len(match_summary) >= len(candidate_selectors):
                logger.info("[Deep Agent ReAct] [TURN %d] [VERIFIED] All fields matched real DOM elements live!", turn)
                is_verified = True
                break
            else:
                logger.warning("[Deep Agent ReAct] [TURN %d] [REFLECTION] Validation failed for fields: %s", turn, failing_fields)

                # Extract context snippet of the repeating layout generically using HTML5 semantic elements
                content_container = soup_page.find(["main", "article"]) or soup_page.find("body") or soup_page
                sample_item = (
                    content_container.find("article")
                    or content_container.find("li")
                    or content_container.find("tr")
                    or content_container.find(attrs={"class": re.compile(r"item|card|row|result|company", re.I)})
                    or content_container
                )
                sample_snippet = str(sample_item)[:1200]

                feedback_msg = (
                    f"Observation from live browser testing:\n"
                    f"Errors:\n" + "\n".join(error_details) + "\n\n"
                    f"Sample element snippet from live page:\n{sample_snippet}\n\n"
                    f"Reflect on why the selectors failed. Check for invalid syntax, or inspect the DOM snippet closely. "
                    f"Provide corrected CSS selectors for ALL fields in the required JSON format."
                )
                conversation_messages.append({"role": "user", "content": feedback_msg})

        # -------------------------------------------------------------
        # Final Stage: Candidate Submission (Tool: submit_candidate_configuration)
        # -------------------------------------------------------------
        logger.info("[Deep Agent ReAct] [STAGE 4: SUBMISSION] Invoking tool: submit_candidate_configuration")
        submit_res = await self.execute_tool("submit_candidate_configuration", {
            "draft_id": "prompt_draft",
            "selector_map": candidate_selectors,
            "rationale": rationale,
            "evidence_refs": [evidence_ref] if evidence_ref else [],
        })
        logger.info("[Deep Agent ReAct] [STAGE 4: SUBMITTED] Candidate accepted by tool harness: %s", submit_res.get("accepted", True))
        logger.info("[Deep Agent ReAct] [COMPLETE] ReAct synthesis completed in %d turns. Verified: %s", turn, is_verified)
        logger.info("================================================================================")

        return {
            "name": discovered_name,
            "target_url": discovered_url or target_url,
            "schema_definition": schema_def,
            "selectors": candidate_selectors,
            "rationale": rationale,
            "evidence_ref": evidence_ref,
            "verified": is_verified,
            "react_turns": turn,
            "inputs": discovered_inputs,
        }
