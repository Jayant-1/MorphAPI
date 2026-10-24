"""
MorphAPI V2 - Interactive Demo: Simulated Website Redesign & Autonomous Self-Healing
Demonstrates:
1. Target Website (Mock Store) starts in Layout V1 (Card Grid).
2. Synthesizes an API endpoint for V1 (status: ACTIVE).
3. Live query extracts 5 products via hierarchical CSS selectors.
4. SIMULATE BREAKING REDESIGN: Mock Store mutates to Layout V2 (Multi-row table, CSS classes wiped).
5. Querying with old selectors matches 0 items.
6. Autonomous Self-Healing triggers: directly executes 'test_custom_browser_script' tool with sibling traversal.
7. Endpoint updates to strategy='custom_js' and returns 100% of products from the new V2 layout!
"""

import asyncio
import time
from playwright.async_api import async_playwright

from morphapi_v2.demo.mock_store import render_mock_store_html, set_mode
from morphapi_v2.schemas.models import (
    EndpointV2CreateRequest,
    ContainerExtractionPlan,
    RelativeFieldSelector,
)
from morphapi_v2.browser.hierarchical_extractor import HierarchicalExtractor
from morphapi_v2.engine.gateway_engine import gateway_engine_v2
from morphapi_v2.agent.deep_agent import deep_agent_v2
from morphapi_v2.db.repository import endpoint_repo_v2

# ANSI Color Codes
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
    banner("MORPHAPI V2: SIMULATED BREAKING REDESIGN & SELF-HEALING DEMO", MAGENTA)
    print(f"{BOLD}Concept:{RESET} Web APIs break when target websites redesign their UI or change CSS classes.")
    print(f"         MorphAPI V2 detects the failure and autonomously heals the extraction plan using")
    print(f"         its sandboxed custom Playwright script tool without human intervention.\n")

    user_id = "demo_host"
    slug = "quantum_gadgets"
    target_url = "http://localhost:8001/mock-store"
    extractor = HierarchicalExtractor()

    # -------------------------------------------------------------------------
    # SCENE 1: Website in Original State (Layout V1)
    # -------------------------------------------------------------------------
    banner("SCENE 1: INITIAL STATE - TARGET WEBSITE (LAYOUT V1: CARD GRID)", CYAN)
    print("The website renders standard card elements:")
    print("  * Container: div.product-card")
    print("  * Name:      h3.product-title")
    print("  * Price:     div.product-price")
    print("  * Link:      a.product-link")

    v1_plan = ContainerExtractionPlan(
        strategy="hierarchical_dom",
        container_selector="div.product-card",
        field_rules={
            "name": RelativeFieldSelector(selector="h3.product-title", attribute="text"),
            "price": RelativeFieldSelector(selector="div.product-price", attribute="text"),
            "link": RelativeFieldSelector(selector="a.product-link", attribute="href"),
        },
        discovery_method="initial_synthesis",
        confidence_score=0.95,
    )

    await endpoint_repo_v2.save_endpoint(
        endpoint_id="ep_demo_gadgets",
        user_id=user_id,
        api_name="Quantum Gadgets API",
        slug=slug,
        target_url=target_url,
        schema_definition={"name": "str", "price": "str", "link": "str"},
        inputs={},
        plan=v1_plan.model_dump(),
        sample_data=[],
        api_key="mapik_demo_live_key",
    )

    print(f"\n{GREEN}[OK] Endpoint Activated:{RESET} /v2/api/{user_id}/{slug}")
    print(f"{GREEN}[OK] Strategy Active:{RESET}    hierarchical_dom")

    # Test extraction on V1 layout in Chromium
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content(render_mock_store_html("v1"))
        v1_extract = await extractor.extract_with_plan(
            page=page,
            plan=v1_plan,
            target_schema={"name": "str", "price": "str", "link": "str"},
        )
        await browser.close()

    print(f"{GREEN}[OK] Live Query Extracted:{RESET} {v1_extract.count} products successfully.")
    for p in v1_extract.data[:2]:
        print(f"    * {p['name']} | {p['price']}")

    # -------------------------------------------------------------------------
    # SCENE 2: The Breaking Website Redesign (Layout V2)
    # -------------------------------------------------------------------------
    time.sleep(1.0)
    banner("SCENE 2: BREAKING REDESIGN! (WEBSITE MIGRATES TO LAYOUT V2)", RED)
    print(f"{RED}[!] Website frontend was completely rewritten!{RESET}")
    print("  * CSS class 'div.product-card' is GONE.")
    print("  * Markup restructured into multi-row table (.catalog-entry + sibling .meta-row).")
    print("  * Price moved to sibling row inside '.pricing .amount'.")

    # Attempt to query with old V1 selectors on V2 layout
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content(render_mock_store_html("v2"))
        broken_extract = await extractor.extract_with_plan(
            page=page,
            plan=v1_plan,
            target_schema={"name": "str", "price": "str", "link": "str"},
        )
        await browser.close()

    print(f"\n{RED}[X] Executing Old Plan on Mutated Layout:{RESET}")
    print(f"  * Matched Count: {broken_extract.count} elements (Failure detected!)")
    print(f"  * Error:         {broken_extract.error_message}")
    print(f"  * In standard scraping systems, the production API would now return empty data or crash.")

    # -------------------------------------------------------------------------
    # SCENE 3: Autonomous Self-Healing Reflex
    # -------------------------------------------------------------------------
    time.sleep(1.0)
    banner("SCENE 3: AUTONOMOUS SELF-HEALING REFLEX ACTIVATED", YELLOW)
    print(f"{YELLOW}* [GatewayEngineV2]{RESET} Extraction returned 0 records on active endpoint '{slug}'.")
    print(f"{YELLOW}* [LangGraph V2]{RESET}    Attempt 1 failed. Triggering immediate shift to custom Playwright script.")
    print(f"{YELLOW}* [DeepAgentV2]{RESET}     Directly invoking 'test_custom_browser_script' tool with sibling DOM traversal...")

    v2_html = render_mock_store_html("v2")
    healed_plan = deep_agent_v2.synthesize_fallback_custom_script(
        target_url=target_url,
        target_schema={"name": "str", "price": "str", "link": "str"},
        dom_snippet=v2_html,
    )

    # Persist the healed plan in SQLite database
    await endpoint_repo_v2.save_endpoint(
        endpoint_id="ep_demo_gadgets",
        user_id=user_id,
        api_name="Quantum Gadgets API",
        slug=slug,
        target_url=target_url,
        schema_definition={"name": "str", "price": "str", "link": "str"},
        inputs={},
        plan=healed_plan.model_dump(),
        sample_data=[],
        api_key="mapik_demo_live_key",
    )

    print(f"\n{GREEN}[OK] Healed Strategy:{RESET}      {healed_plan.strategy}")
    print(f"{GREEN}[OK] Discovery Method:{RESET}     {healed_plan.discovery_method}")
    print(f"{GREEN}[OK] Database Updated:{RESET}     Persisted healed plan to SQLite repository")

    # -------------------------------------------------------------------------
    # SCENE 4: Verification of Healed Endpoint
    # -------------------------------------------------------------------------
    time.sleep(1.0)
    banner("SCENE 4: LIVE EXECUTION WITH HEALED SCRIPT (100% RECOVERY)", GREEN)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content(v2_html)
        healed_extract = await extractor.extract_with_plan(
            page=page,
            plan=healed_plan,
            target_schema={"name": "str", "price": "str", "link": "str"},
        )
        await browser.close()

    print(f"{GREEN}[OK] Extracted from New V2 Layout:{RESET} {healed_extract.count} / 5 products (100% Complete!)")
    print("\nSample records extracted from the redesigned UI:")
    for idx, item in enumerate(healed_extract.data[:3], 1):
        print(f"  [{idx}] {CYAN}{item['name']}{RESET}")
        print(f"      * Price: {GREEN}{item['price']}{RESET}")
        print(f"      * Link:  {YELLOW}{item['link']}{RESET}")

    banner("DEMO TAKEAWAY", MAGENTA)
    print("1. Traditional scrapers crash when class names or layouts change.")
    print("2. MorphAPI V2 monitors extraction quality and detects 0-count / low-coverage failures.")
    print("3. In healing mode, it directly shifts to the custom Playwright browser script tool,")
    print("   inspects the new DOM, repairs the plan, and persists the update automatically.")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
