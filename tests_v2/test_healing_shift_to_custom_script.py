"""
Unit Tests for Healing Shift to Custom Script in MorphAPI V2
Verifies that when hierarchical extraction fails on Attempt 1, the workflow immediately shifts to custom_js.
"""

import pytest
from morphapi_v2.workflows.graph import morphapi_workflow_v2
from morphapi_v2.agent.deep_agent import deep_agent_v2
from morphapi_v2.schemas.models import ContainerExtractionPlan, RelativeFieldSelector


@pytest.mark.asyncio
async def test_reflect_and_heal_shifts_to_custom_script():
    """Verify that after Attempt 1 fails validation, reflect_and_heal shifts to custom_js."""
    initial_state = {
        "prompt": "Extract articles and dates from https://news.ycombinator.com/",
        "target_url": "https://news.ycombinator.com/",
        "inspection_url": "https://news.ycombinator.com/",
        "turn": 1,
        "max_turns": 3,
        "intent": {
            "name": "hn_articles",
            "slug": "hn-articles",
            "schema_definition": {"title": "str", "the_date": "str", "link": "str"},
            "inputs": {},
        },
        "plan": {
            "strategy": "hierarchical_dom",
            "container_selector": "table tbody tr",
            "field_rules": {
                "title": {"selector": "a", "attribute": "text"},
                "the_date": {"selector": "td.subtext", "attribute": "text"},
                "link": {"selector": "a", "attribute": "href"},
            },
        },
        "validation_issues": ["Primary field 'the_date' has low coverage: 7.1% (expected >= 60.0%)"],
        "status": "HEALING",
    }

    healed_update = await morphapi_workflow_v2._reflect_and_heal_node(initial_state)

    assert healed_update["turn"] == 2
    assert healed_update["status"] == "TESTING"
    healed_plan = healed_update["plan"]
    # Must immediately switch to custom_js after 1 failed attempt!
    assert healed_plan["strategy"] == "custom_js"
    assert healed_plan["custom_js_extractor"] is not None
    assert len(healed_plan["custom_js_extractor"]) > 20


@pytest.mark.asyncio
async def test_propose_plan_force_custom_script():
    """Verify that propose_plan returns custom_js and does not fall back to DOM cluster analyzer when force_custom_script=True."""
    plan = await deep_agent_v2.propose_plan(
        target_schema={"title": "str", "the_date": "str", "link": "str"},
        dom_snippet="<table><tr class='athing'><td><a href='/1'>Title</a></td></tr><tr><td class='subtext'><span class='age'>3 hours ago</span></td></tr></table>",
        target_url="https://news.ycombinator.com/",
        previous_error="Primary field 'the_date' has low coverage: 7.1%",
        force_custom_script=True,
    )

    assert plan.strategy == "custom_js"
    assert plan.custom_js_extractor is not None
    assert "the_date" in plan.custom_js_extractor
    assert "nextElementSibling" in plan.custom_js_extractor
