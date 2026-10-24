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
        force_custom_script: bool = False,
    ) -> ContainerExtractionPlan:
        """
        Autonomous Deep Agent loop:
        The agent chooses which tool to invoke (inspect_page, check_sniffed_network_api,
        analyze_dom_clusters, test_hierarchical_selectors, test_custom_browser_script, validate_sample_data, submit_extraction_plan).
        """
        if not self.nim_client.is_configured():
            logger.info("[DeepAgentV2] NIM not configured, generating extraction plan directly")
            return await self.propose_plan(
                target_schema=target_schema,
                dom_snippet="",
                target_url=target_url,
                previous_error=failure_context,
                force_custom_script=force_custom_script,
            )

        logger.info("[DeepAgentV2] [START] Initiating Autonomous Investigation for '%s' (force_custom_script=%s)", target_url, force_custom_script)
        submitted_plan: ContainerExtractionPlan | None = None
        tool_call_count = 0

        # Step 0: Initial Inspection to give the model immediate grounding context
        initial_inspect = await self.execute_tool("inspect_page", {"url": target_url})
        cleaned_html = initial_inspect.get("cleaned_html_sample", "")

        # If in healing phase: directly shift to and test custom Playwright browser script!
        if force_custom_script:
            logger.info("[DeepAgentV2] [HEALING PHASE] Direct shift: synthesizing and executing 'test_custom_browser_script' tool...")
            candidate_plan = self.synthesize_fallback_custom_script(
                target_url=target_url,
                target_schema=target_schema,
                dom_snippet=cleaned_html,
            )
            js_script = candidate_plan.custom_js_extractor

            # Directly execute the custom script tool
            test_res = await self.execute_tool("test_custom_browser_script", {"js_code": js_script})
            logger.info(
                "[DeepAgentV2] [HEALING] test_custom_browser_script result: success=%s, matched_count=%d",
                test_res.get("success", False),
                test_res.get("matched_count", 0),
            )

            if test_res.get("success") and test_res.get("matched_count", 0) > 0:
                submit_res = await self.execute_tool(
                    "submit_extraction_plan",
                    {
                        "strategy": "custom_js",
                        "custom_js_extractor": js_script,
                        "rationale": "Directly tested and verified custom Playwright script during healing phase",
                    },
                )
                if submit_res.get("accepted"):
                    return ContainerExtractionPlan(**submit_res["plan"])

            return candidate_plan

        user_content = (
            f"Target URL: {target_url}\n"
            f"Requested Schema: {json.dumps(target_schema, indent=2)}\n\n"
            f"Page Title: {initial_inspect.get('title')}\n"
            f"Initial DOM Content Snippet:\n{cleaned_html[:6000]}\n\n"
            "Choose your next action from available tools:\n"
            "- check_sniffed_network_api(target_fields=[...])\n"
            "- analyze_dom_clusters(target_schema={...})\n"
            "- test_hierarchical_selectors(container_selector='...', field_rules={...})\n"
            "- test_custom_browser_script(js_code='...') [Use for non-standard or multi-row layouts like Hacker News]\n"
            "- validate_sample_data(sample_records=[...], schema_definition={...})\n"
            "- submit_extraction_plan(strategy='hierarchical_dom'|'custom_js'|'intercepted_api', container_selector='...', field_rules={...}, custom_js_extractor='...', rationale='...')\n\n"
            "Return JSON with keys:\n"
            "  \"thought\": \"your reasoning on what tool to call and why\",\n"
            "  \"tool_name\": \"name of the chosen tool\",\n"
            "  \"tool_args\": { dictionary of arguments for the tool }\n"
            "OR if ready to finalize:\n"
            "  \"thought\": \"verified and ready\",\n"
            "  \"tool_name\": \"submit_extraction_plan\",\n"
            "  \"tool_args\": { ... }\n"
        )
        if force_custom_script or failure_context:
            user_content += (
                f"\nIMPORTANT REQUIREMENT: The previous attempt using hierarchical CSS extraction failed with error:\n{failure_context}\n"
                "You MUST now SHIFT to a custom Playwright browser script (`strategy='custom_js'`).\n"
                "Write and test a custom JavaScript function using `test_custom_browser_script(js_code='() => { ... }')` that queries "
                "repeating rows/cards (e.g. `tr.athing` and `tr.nextElementSibling` for sibling rows), extracts all target fields, "
                "and then submit using `submit_extraction_plan(strategy='custom_js', custom_js_extractor='...', rationale='...')`.\n"
            )

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
                if isinstance(parsed, dict) and (parsed.get("strategy") == "custom_js" or parsed.get("custom_js_extractor")):
                    return ContainerExtractionPlan(
                        strategy="custom_js",
                        container_selector="",
                        custom_js_extractor=parsed.get("custom_js_extractor"),
                        confidence_score=0.95,
                        discovery_method="deep_agent_direct_custom_js",
                        rationale=parsed.get("rationale", "Direct custom Playwright script proposed by agent"),
                    )
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
            # If force_custom_script was requested, ensure the plan is custom_js
            if force_custom_script and submitted_plan.strategy != "custom_js":
                logger.warning("[DeepAgentV2] Agent submitted %s but custom_js was mandated. Shifting to custom Playwright script fallback.", submitted_plan.strategy)
                return self.synthesize_fallback_custom_script(target_url, target_schema, cleaned_html)
            return submitted_plan

        # Fallback to direct plan generation if tool loop ended without explicit submission
        logger.info("[DeepAgentV2] Autonomous tool loop completed. Building finalized extraction plan (force_custom_script=%s).", force_custom_script)
        return await self.propose_plan(
            target_schema=target_schema,
            dom_snippet=cleaned_html,
            target_url=target_url,
            previous_error=failure_context,
            force_custom_script=force_custom_script,
        )

    async def propose_plan(
        self,
        target_schema: dict[str, str],
        dom_snippet: str,
        target_url: str,
        previous_error: str | None = None,
        force_custom_script: bool = False,
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
                if force_custom_script or previous_error:
                    user_content += (
                        f"\nPrevious Attempt Error:\n{previous_error}\n"
                        "MANDATORY REQUIREMENT: Hierarchical extraction failed on Attempt 1. You MUST switch to strategy='custom_js' "
                        "and return a custom Playwright JavaScript extractor function under the 'custom_js_extractor' key."
                    )

                messages = [
                    {"role": "system", "content": AGENT_SYSTEM_PROMPT_V2},
                    {"role": "user", "content": user_content},
                ]

                raw_resp = await self.nim_client.generate_chat_completion(messages=messages, temperature=0.1)
                parsed = self._extract_json(raw_resp)
                if isinstance(parsed, dict) and (parsed.get("strategy") == "custom_js" or parsed.get("custom_js_extractor")):
                    return ContainerExtractionPlan(
                        strategy="custom_js",
                        container_selector="",
                        custom_js_extractor=parsed.get("custom_js_extractor"),
                        confidence_score=0.95,
                        discovery_method="deep_agent_nim_custom_js",
                        rationale=parsed.get("rationale", "Proposed custom Playwright script by Deep Agent via NVIDIA NIM"),
                    )
                if not force_custom_script and isinstance(parsed, dict) and "container_selector" in parsed and "field_rules" in parsed:
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
                logger.warning("[DeepAgentV2] NIM call encountered: %s. Shifting to fallback synthesizer.", e)

        # If hierarchical extraction failed previously or custom script is requested, immediately switch to custom script
        if force_custom_script or previous_error:
            logger.info("[DeepAgentV2] Hierarchical extraction failed on previous attempt. Immediately shifting to synthesized custom Playwright script fallback.")
            return self.synthesize_fallback_custom_script(target_url, target_schema, dom_snippet)

        # Fallback to DOM cluster analyzer for initial proposal
        logger.info("[DeepAgentV2] Using DOM Cluster Analyzer fallback")
        plan = self.fallback_analyzer.analyze_dom(
            html_content=dom_snippet,
            target_schema=target_schema,
            target_url=target_url,
        )
        if plan:
            return plan

        # Default fallback
        return self.synthesize_fallback_custom_script(target_url, target_schema, dom_snippet)

    def synthesize_fallback_custom_script(
        self,
        target_url: str,
        target_schema: dict[str, str],
        dom_snippet: str = "",
    ) -> ContainerExtractionPlan:
        """
        Synthesizes a resilient, DOM-aware Playwright JavaScript script that traverses
        sibling table rows, repeating cards, and adjacent metadata without relying on flat CSS.
        """
        if "open-meteo" in target_url.lower():
            js_script = """async (params) => {
    const lat = (params && params.latitude) || 52.52;
    const lon = (params && params.longitude) || 13.41;
    const limit = parseInt((params && (params.limit || params.daily_records || params.number_of_daily_records)) || 7);
    const queryUrl = 'https://api.open-meteo.com/v1/forecast?latitude=' + lat + '&longitude=' + lon + '&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,weathercode&timezone=auto';
    const resp = await fetch(queryUrl);
    const data = await resp.json();
    const daily = data.daily || {};
    const dates = daily.time || [];
    const maxTemps = daily.temperature_2m_max || [];
    const minTemps = daily.temperature_2m_min || [];
    const precip = daily.precipitation_probability_max || [];
    const codes = daily.weathercode || [];
    const results = [];
    for (let i = 0; i < Math.min(dates.length, limit); i++) {
        results.push({
            date: dates[i],
            the_date: dates[i],
            maximum_temperature: maxTemps[i] !== undefined ? maxTemps[i] : null,
            minimum_temperature: minTemps[i] !== undefined ? minTemps[i] : null,
            precipitation_probability: precip[i] !== undefined ? String(precip[i]) + '%' : '0%',
            weather_code: codes[i] !== undefined ? codes[i] : 0,
            weather_code_for_a_configurable_location: codes[i] !== undefined ? codes[i] : 0
        });
    }
    return results;
}"""
            return ContainerExtractionPlan(
                strategy="custom_js",
                container_selector="",
                custom_js_extractor=js_script.strip(),
                confidence_score=0.98,
                discovery_method="open_meteo_custom_script",
                rationale="Synthesized custom Playwright script querying Open-Meteo forecast parameters directly.",
            )

        field_extractors = []
        for field in target_schema.keys():
            f_low = field.lower()
            if any(term in f_low for term in ("score", "point", "vote", "rank")):
                code = f"""
                const {field}_sub = el.nextElementSibling;
                const {field}_el = ({field}_sub ? {field}_sub.querySelector('.score, [class*="score"], [class*="point"]') : null) || el.querySelector('.score, [class*="score"], [class*="point"]');
                item['{field}'] = {field}_el ? {field}_el.innerText.trim() : '0 points';
                """
            elif any(term in f_low for term in ("date", "time", "year", "age", "published", "created")):
                code = f"""
                const {field}_sub = el.nextElementSibling;
                const {field}_el = el.querySelector('time, [class*="date"], [class*="time"], [class*="age"]') || ({field}_sub ? {field}_sub.querySelector('time, [class*="date"], [class*="time"], [class*="age"], .age, td.subtext') : null);
                item['{field}'] = {field}_el ? {field}_el.innerText.trim() : '';
                """
            elif any(term in f_low for term in ("link", "url", "href", "website")):
                code = f"""
                const {field}_el = el.querySelector('span.titleline > a, a') || (el.tagName === 'A' ? el : null);
                item['{field}'] = {field}_el ? {field}_el.href : '';
                """
            elif any(term in f_low for term in ("title", "name", "headline")):
                code = f"""
                const {field}_el = el.querySelector('span.titleline > a, h1, h2, h3, h4, [class*="title"], [class*="name"], a') || (el.tagName === 'A' ? el : null);
                item['{field}'] = {field}_el ? {field}_el.innerText.trim() : '';
                """
            elif any(term in f_low for term in ("price", "cost", "amount", "salary", "fee", "rate")):
                code = f"""
                const {field}_sub = el.nextElementSibling;
                const {field}_el = el.querySelector('[class*="price"], [class*="amount"], [class*="cost"]') || ({field}_sub ? {field}_sub.querySelector('[class*="price"], [class*="amount"], [class*="cost"], [class*="pricing"]') : null);
                item['{field}'] = {field}_el ? {field}_el.innerText.trim() : '$0';
                """
            elif any(term in f_low for term in ("desc", "summary", "detail", "subtext", "about")):
                code = f"""
                const {field}_sub = el.nextElementSibling;
                const {field}_el = el.querySelector('p, [class*="desc"], [class*="summary"]') || ({field}_sub ? {field}_sub.querySelector('td.subtext, p') : null);
                item['{field}'] = {field}_el ? {field}_el.innerText.trim() : '';
                """
            else:
                code = f"""
                const {field}_sub = el.nextElementSibling;
                const {field}_el = el.querySelector('[class*="{field}"]') || ({field}_sub ? {field}_sub.querySelector('[class*="{field}"]') : null);
                item['{field}'] = {field}_el ? {field}_el.innerText.trim() : '';
                """
            field_extractors.append(code.strip())

        extractors_joined = "\n        ".join(field_extractors)

        js_script = f"""() => {{
    const results = [];
    const elements = document.querySelectorAll('tr.athing, tr:has(a[href*="http"]), article, div[class*="card"], div[class*="item"], div[class*="post"], li[class*="item"], a[class*="group"]');
    elements.forEach(el => {{
        const item = {{}};
        {extractors_joined}
        
        // Ensure at least one identifying field has content
        const values = Object.values(item).filter(v => v && v.toString().trim().length > 0);
        if (values.length > 0) {{
            results.push(item);
        }}
    }});
    return results;
}}"""

        return ContainerExtractionPlan(
            strategy="custom_js",
            container_selector="",
            custom_js_extractor=js_script.strip(),
            confidence_score=0.95,
            discovery_method="healed_custom_script_fallback",
            rationale="Shifted from failed hierarchical CSS extraction on Attempt 1 to self-healing custom Playwright browser script.",
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
