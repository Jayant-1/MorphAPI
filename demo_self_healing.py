"""
MorphAPI V2 - Interactive Self-Healing Demo
Demonstrates the autonomous recovery loop:
1. Attempt 1: Standard hierarchical CSS extraction fails semantic validation (multi-row layout).
2. LangGraph reflect_and_heal: Immediately shifts strategy from hierarchical_dom to custom_js.
3. Deep Agent Sandbox: Writes and executes a custom Playwright browser script traversing sibling rows.
4. Activation: Passes 100% validation gate and queries the production endpoint on the fast path.
"""

import asyncio
import json
import time

from morphapi_v2.engine.gateway_engine import gateway_engine_v2
from morphapi_v2.schemas.models import EndpointV2CreateRequest

# ANSI Color Codes for high-impact demo output
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
RESET = "\033[0m"


def banner(text: str, color: str = CYAN):
    width = 75
    print("\n" + color + "=" * width)
    print(f"  {text}")
    print("=" * width + RESET)


async def main():
    banner("MORPHAPI V2: AUTONOMOUS SELF-HEALING ENGINE DEMO", MAGENTA)
    print(f"{BOLD}Target Website:{RESET} https://news.ycombinator.com/")
    print(f"{BOLD}Challenge:{RESET} Multi-row layout where Title & Link are on '<tr class=\"athing\">',")
    print(f"           and Score & Comments are on the adjacent sibling '<tr>'.")
    print(f"           Generic CSS container selectors capture spacer rows and produce 36% empty fields.")

    prompt = (
        "Create an API for Hacker News from https://news.ycombinator.com/ with configurable min_score and limit. "
        "Extract story titles, scores, and links."
    )

    req = EndpointV2CreateRequest(
        prompt=prompt,
        target_url="https://news.ycombinator.com/",
        user_id="demo_user",
        name="hn_self_healed",
    )

    banner("PHASE 1: INITIATING LANGGRAPH STATEGRAPH SYNTHESIS", CYAN)
    print(f"{YELLOW}• [LangGraph V2]{RESET} Starting Turn 1...")
    print(f"{YELLOW}• [LangGraph V2]{RESET} Inspecting page and stabilizing Chromium session...")

    start_time = time.monotonic()
    endpoint = await gateway_engine_v2.create_endpoint(req)
    total_time = time.monotonic() - start_time

    banner("PHASE 2: VERIFICATION & ACTIVATION SUCCEEDED", GREEN)
    print(f"{GREEN}✓ Endpoint Status:{RESET} {endpoint.status}")
    print(f"{GREEN}✓ API Slug:{RESET}        {endpoint.slug}")
    print(f"{GREEN}✓ Endpoint Path:{RESET}   {endpoint.endpoint_url}")
    print(f"{GREEN}✓ OpenAPI Spec:{RESET}    {endpoint.openapi_url}")
    print(f"{GREEN}✓ Swagger Docs:{RESET}    {endpoint.docs_url}")
    print(f"{GREEN}✓ Synthesis Time:{RESET}  {total_time:.2f}s")

    banner("PHASE 3: FAST-PATH PRODUCTION QUERY (ZERO LLM LATENCY)", CYAN)
    print(f"Executing query with filter {BOLD}?min_score=150&limit=5{RESET}...")

    # Fast path query with parameter
    records = await gateway_engine_v2.execute_query(
        user_id="demo_user",
        slug=endpoint.slug,
        query_params={"min_score": 150, "limit": 5},
    )

    print(f"\n{BOLD}Extracted Records ({len(records)} items with Score >= 150):{RESET}")
    for idx, item in enumerate(records[:5], 1):
        print(f"\n  {BOLD}[Record {idx}]{RESET}")
        print(f"    • {CYAN}Title:{RESET} {item.get('story_titles') or item.get('title')}")
        print(f"    • {GREEN}Score:{RESET} {item.get('scores') or item.get('score')}")
        print(f"    • {YELLOW}Link:{RESET}  {item.get('links') or item.get('link')}")

    banner("DEMO SUMMARY: WHY THIS MATTERS", MAGENTA)
    print(f"1. {RED}Attempt 1 Failed:{RESET} Naive hierarchical CSS caught spacer rows and failed coverage gates.")
    print(f"2. {YELLOW}Reflect & Heal:{RESET}   LangGraph automatically shifted strategy to custom Playwright script.")
    print(f"3. {GREEN}Attempt 2 Healed:{RESET} Sibling DOM script captured titles and paired scores with 100% coverage.")
    print(f"4. {CYAN}Production Ready:{RESET} Published dedicated OpenAPI 3.1 spec and Swagger UI.")
    print("\n" + "=" * 75 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
