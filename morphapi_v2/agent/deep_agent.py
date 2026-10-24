"""
Deep Agent Planning Harness for MorphAPI V2
Provides autonomous tool selection, multi-turn ReAct loop (Thought -> Action -> Observation),
and bounded planning over specialized scraping tools.
"""

import json
import logging
import re
import time
from typing import Any

from morphapi_v2.agent.nim_client import NimClientV2, nim_client_v2
from morphapi_v2.agent.prompts import AGENT_SYSTEM_PROMPT_V2
from morphapi_v2.agent.tools import AgentToolRegistryV2, tool_registry_v2
from morphapi_v2.schemas.models import ContainerExtractionPlan, RelativeFieldSelector
from morphapi_v2.browser.dom_cluster import dom_cluster_analyzer

logger = logging.getLogger("morphapi_v2.deep_agent")


class DeepAgentHarnessV2:
    def __init__(
        self,
        nim_client: NimClientV2 | None = None,
        tool_registry: AgentToolRegistryV2 | None = None,
        max_tool_calls: int = 6,
    ):
        self.nim_client = nim_client or nim_client_v2
        self.tool_registry = tool_registry or tool_registry_v2
        self.fallback_analyzer = dom_cluster_analyzer
        self.max_tool_calls = max_tool_calls

    async def execute_tool(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Executes a registered tool by name with arguments."""
        tool_fn = getattr(self.tool_registry, tool_name, None)
        if not tool_fn or not callable(tool_fn):
            return {"error": f"Tool '{tool_name}' is not registered or disallowed"}

        try:
            logger.info("[DeepAgentV2] [ACTION] Executing tool: %s(args=%s)", tool_name, args)
            res = await tool_fn(**args)
            return res
        except Exception as e:
            logger.warning("[DeepAgentV2] Tool '%s' execution error: %s", tool_name, e)
            return {"error": str(e)}

    async def autonomous_investigation(
        self,
        target_url: str,
        target_schema: dict[str, str],
        failure_context: str | None = None,
    ) -> ContainerExtractionPlan:
        """
        Autonomous Deep Agent loop:
        The agent chooses which tool to invoke (inspect_page, check_sniffed_network_api,
        analyze_dom_clusters, test_hierarchical_selectors, validate_sample_data, submit_extraction_plan).
        """
        if not self.nim_client.is_configured():
            logger.info("[DeepAgentV2] NIM not configured, using direct DOM Cluster Analyzer")
            return await self.propose_plan(target_schema, "", target_url)

        logger.info("[DeepAgentV2] [START] Initiating Autonomous Investigation for '%s'", target_url)
        submitted_plan: ContainerExtractionPlan | None = None
        tool_call_count = 0

        # Step 0: Initial Inspection to give the model immediate grounding context
        initial_inspect = await self.execute_tool("inspect_page", {"url": target_url})
        cleaned_html = initial_inspect.get("cleaned_html_sample", "")

        user_content = (
            f"Target URL: {target_url}\n"
            f"Requested Schema: {json.dumps(target_schema, indent=2)}\n\n"
            f"Page Title: {initial_inspect.get('title')}\n"
            f"Initial DOM Content Snippet:\n{cleaned_html[:6000]}\n\n"
            "Choose your next action from available tools:\n"
            "- check_sniffed_network_api(target_fields=[...])\n"
            "- analyze_dom_clusters(target_schema={...})\n"
            "- test_hierarchical_selectors(container_selector='...', field_rules={...})\n"
            "- validate_sample_data(sample_records=[...], schema_definition={...})\n"
            "- submit_extraction_plan(strategy='...', container_selector='...', field_rules={...}, rationale='...')\n\n"
            "Return JSON with keys:\n"
            "  \"thought\": \"your reasoning on what tool to call and why\",\n"
            "  \"tool_name\": \"name of the chosen tool\",\n"
            "  \"tool_args\": { dictionary of arguments for the tool }\n"
            "OR if ready to finalize:\n"
            "  \"thought\": \"verified and ready\",\n"
            "  \"tool_name\": \"submit_extraction_plan\",\n"
            "  \"tool_args\": { ... }\n"
        )
        if failure_context:
            user_content += f"\nPrevious Attempt Error:\n{failure_context}\n"

        conversation = [
            {"role": "system", "content": AGENT_SYSTEM_PROMPT_V2},
            {"role": "user", "content": user_content},
        ]

        while tool_call_count < self.max_tool_calls:
            tool_call_count += 1
            try:
                raw_resp = await self.nim_client.generate_chat_completion(
                    messages=conversation,
                    temperature=0.1,
                )
            except Exception as e:
                logger.warning("[DeepAgentV2] NIM call error on turn %d: %s. Falling back to direct proposal.", tool_call_count, e)
                break

            parsed = self._extract_json(raw_resp)
            if not isinstance(parsed, dict) or "tool_name" not in parsed:
                # If model directly returned a plan
                if isinstance(parsed, dict) and "container_selector" in parsed:
                    field_rules = self._parse_field_rules(parsed.get("field_rules", {}), target_schema)
                    return ContainerExtractionPlan(
                        strategy="hierarchical_dom",
                        container_selector=parsed["container_selector"],
                        field_rules=field_rules,
                        confidence_score=0.9,
                        discovery_method="deep_agent_direct_plan",
                    )
                break

            tool_name = parsed["tool_name"]
            tool_args = parsed.get("tool_args", {})
            thought = parsed.get("thought", "")
            logger.info("[DeepAgentV2] [THOUGHT] %s", thought)
            logger.info("[DeepAgentV2] [CHOSEN TOOL %d/%d] %s", tool_call_count, self.max_tool_calls, tool_name)

            if tool_name == "submit_extraction_plan":
                submit_res = await self.execute_tool(tool_name, tool_args)
                if submit_res.get("accepted"):
                    submitted_plan = ContainerExtractionPlan(**submit_res["plan"])
                    break

            # Execute tool and record observation
            tool_res = await self.execute_tool(tool_name, tool_args)
            logger.info("[DeepAgentV2] [OBSERVATION] %s", str(tool_res)[:200])

            conversation.append({"role": "assistant", "content": raw_resp})
            conversation.append({
                "role": "user",
                "content": f"Observation from '{tool_name}':\n{json.dumps(tool_res, default=str)}\n\nWhat is your next thought and tool choice?",
            })

        if submitted_plan:
            return submitted_plan

        # Fallback to direct plan generation if tool loop ended without explicit submission
        logger.info("[DeepAgentV2] Autonomous tool loop completed. Building finalized extraction plan.")
        return await self.propose_plan(target_schema, cleaned_html, target_url, previous_error=failure_context)

    async def propose_plan(
        self,
        target_schema: dict[str, str],
        dom_snippet: str,
        target_url: str,
        previous_error: str | None = None,
    ) -> ContainerExtractionPlan:
        """Direct one-shot or reflective proposal method."""
        if self.nim_client.is_configured():
            try:
                clean_soup = self.fallback_analyzer.clean_html(dom_snippet)
                content_root = (
                    clean_soup.find(["main", "article"])
                    or clean_soup.find(id=re.compile(r"content|app|root", re.I))
                    or clean_soup.body
                    or clean_soup
                )
                clean_snippet = str(content_root)[:12000]

                user_content = (
                    f"Target URL: {target_url}\n"
                    f"Requested Schema: {json.dumps(target_schema, indent=2)}\n\n"
                    f"Cleaned DOM Content Snippet:\n{clean_snippet}\n"
                )
                if previous_error:
                    user_content += f"\nPrevious Attempt Error:\n{previous_error}\nPlease self-correct the selectors."

                messages = [
                    {"role": "system", "content": AGENT_SYSTEM_PROMPT_V2},
                    {"role": "user", "content": user_content},
                ]

                raw_resp = await self.nim_client.generate_chat_completion(messages=messages, temperature=0.1)
                parsed = self._extract_json(raw_resp)
                if isinstance(parsed, dict) and "container_selector" in parsed and "field_rules" in parsed:
                    field_rules = self._parse_field_rules(parsed["field_rules"], target_schema)
                    return ContainerExtractionPlan(
                        strategy="hierarchical_dom",
                        container_selector=parsed["container_selector"],
                        field_rules=field_rules,
                        confidence_score=0.92,
                        discovery_method="deep_agent_nim",
                        rationale=parsed.get("rationale", "Proposed by Deep Agent via NVIDIA NIM"),
                    )
            except Exception as e:
                logger.warning("[DeepAgentV2] NIM call encountered: %s. Falling back to DOM Cluster Analyzer.", e)

        # Fallback to DOM cluster analyzer
        logger.info("[DeepAgentV2] Using DOM Cluster Analyzer fallback")
        plan = self.fallback_analyzer.analyze_dom(
            html_content=dom_snippet,
            target_schema=target_schema,
            target_url=target_url,
        )
        if plan:
            return plan

        # Default resilient fallback matching common directory/card elements
        field_rules = {}
        for k in target_schema.keys():
            attr = "href" if any(term in k for term in ("link", "url", "href")) else "text"
            field_rules[k] = RelativeFieldSelector(selector="a" if attr == "href" else ".", attribute=attr)

        return ContainerExtractionPlan(
            strategy="hierarchical_dom",
            container_selector="a[class*='company'], a[class*='group'], a[href*='/companies/'], div.card, article",
            field_rules=field_rules,
            confidence_score=0.7,
            discovery_method="resilient_card_heuristic",
        )

    def _parse_field_rules(self, raw_rules: dict[str, Any], target_schema: dict[str, str]) -> dict[str, RelativeFieldSelector]:
        field_rules = {}
        for k in target_schema.keys():
            v = raw_rules.get(k, {})
            if isinstance(v, dict):
                field_rules[k] = RelativeFieldSelector(
                    selector=v.get("selector", "."),
                    attribute=v.get("attribute", "href" if any(term in k for term in ("link", "url")) else "text"),
                )
            elif isinstance(v, str):
                field_rules[k] = RelativeFieldSelector(
                    selector=v,
                    attribute="href" if any(term in k for term in ("link", "url")) else "text",
                )
            else:
                field_rules[k] = RelativeFieldSelector(
                    selector="." if any(term in k for term in ("link", "url")) else "h3, span, p",
                    attribute="href" if any(term in k for term in ("link", "url")) else "text",
                )
        return field_rules

    def _extract_json(self, text: str) -> dict[str, Any] | None:
        try:
            return json.loads(text)
        except Exception:
            pass
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception:
                pass
        match = re.search(r"(\{[\s\S]*\})", text)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception:
                pass
        return None


deep_agent_v2 = DeepAgentHarnessV2()
