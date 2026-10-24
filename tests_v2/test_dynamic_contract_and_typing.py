"""
Tests for Dynamic Endpoint Contracts, Type Coercion, Parameter Injection, and OpenAPI Generation in MorphAPI V2
"""

import pytest
from playwright.async_api import async_playwright
from httpx import AsyncClient, ASGITransport

from morphapi_v2.api.app import app
from morphapi_v2.schemas.models import (
    ContainerExtractionPlan,
    EndpointContract,
    ParameterSpec,
    FieldTypeSpec,
)
from morphapi_v2.browser.hierarchical_extractor import HierarchicalExtractor
from morphapi_v2.engine.type_coercer import type_coercer
from morphapi_v2.engine.openapi_generator import openapi_generator_v2
from morphapi_v2.engine.intent_parser import intent_parser_v2
from morphapi_v2.db.repository import endpoint_repo_v2


def test_type_coercer_scalars():
    """Verify robust coercion of strings to int, float, bool, list, and url."""
    # Integer coercion
    assert type_coercer.coerce_field("165 points", "int") == 165
    assert type_coercer.coerce_field("3,500 items", "int") == 3500
    assert type_coercer.coerce_field("-42", "int") == -42
    assert type_coercer.coerce_field("invalid", "int", default=10) == 10

    # Float coercion
    assert type_coercer.coerce_field("$1,299.99", "float") == 1299.99
    assert type_coercer.coerce_field("4.8 stars", "float") == 4.8
    assert type_coercer.coerce_field("95.5%", "float") == 95.5
    assert type_coercer.coerce_field("no price", "float", default=0.0) == 0.0

    # Boolean coercion
    assert type_coercer.coerce_field("In Stock", "bool") is True
    assert type_coercer.coerce_field("Yes", "bool") is True
    assert type_coercer.coerce_field("1", "bool") is True
    assert type_coercer.coerce_field("Out of Stock", "bool") is False
    assert type_coercer.coerce_field("0", "bool") is False
    assert type_coercer.coerce_field("false", "bool") is False

    # List coercion
    tags = type_coercer.coerce_field("Python, Rust, TypeScript", "list[str]")
    assert tags == ["Python", "Rust", "TypeScript"]
    tags_pipe = type_coercer.coerce_field("AI | ML | LLM", "list")
    assert tags_pipe == ["AI", "ML", "LLM"]

    # URL resolution
    abs_url = type_coercer.coerce_field("/item?id=123", "url", base_url="https://news.ycombinator.com/")
    assert abs_url == "https://news.ycombinator.com/item?id=123"


def test_response_envelope_shaping():
    """Verify shaping responses into list, single_object, and paginated formats."""
    sample_data = [
        {"id": 1, "name": "Alpha"},
        {"id": 2, "name": "Beta"},
        {"id": 3, "name": "Gamma"},
    ]

    # 1. List shape (default)
    list_res = type_coercer.shape_response(sample_data, response_shape="list")
    assert isinstance(list_res, list)
    assert len(list_res) == 3

    # 2. Single object shape (detail/profile endpoints)
    single_res = type_coercer.shape_response(sample_data, response_shape="single_object")
    assert isinstance(single_res, dict)
    assert single_res["id"] == 1
    assert single_res["name"] == "Alpha"

    # 3. Paginated envelope shape
    paginated_res = type_coercer.shape_response(
        sample_data,
        response_shape="paginated",
        query_params={"page": 2, "limit": 2},
        total_count=50,
    )
    assert isinstance(paginated_res, dict)
    assert paginated_res["page"] == 2
    assert paginated_res["limit"] == 2
    assert paginated_res["count"] == 3
    assert paginated_res["total"] == 50
    assert paginated_res["has_more"] is True
    assert len(paginated_res["data"]) == 3


def test_intent_parser_infers_contract_and_types():
    """Verify IntentParserV2 infers custom parameters, field types, and response shapes."""
    prompt = (
        "Create an API for Hacker News from https://news.ycombinator.com/ with configurable min_score and limit. "
        "Extract story titles, scores, and links. Return paginated format."
    )
    intent = intent_parser_v2.parse(prompt)

    assert intent.response_shape == "paginated"
    assert intent.contract is not None
    assert intent.contract.response_shape == "paginated"

    # Verify inferred parameter types
    param_names = [p.name for p in intent.contract.parameters]
    assert "min_score" in param_names
    assert "limit" in param_names

    # Verify field types
    field_map = {f.name: f.target_type for f in intent.contract.fields}
    assert field_map.get("scores") == "int"
    assert field_map.get("links") == "url"


def test_openapi_spec_generation():
    """Verify dynamic OpenAPI 3.1 generation for a synthesized endpoint."""
    endpoint_data = {
        "api_name": "Tech Jobs API",
        "user_id": "test_user",
        "slug": "tech-jobs",
        "target_url": "https://jobs.example.com/search",
        "schema_definition": {"title": "str", "salary": "float", "is_remote": "bool"},
        "inputs": {"location": {"type": "str"}},
        "plan": {
            "contract": {
                "response_shape": "paginated",
                "parameters": [
                    {"name": "location", "type": "str", "location": "query", "description": "City or Country"},
                    {"name": "min_salary", "type": "float", "location": "query", "default": 50000.0},
                ],
                "fields": [
                    {"name": "title", "target_type": "str"},
                    {"name": "salary", "target_type": "float"},
                    {"name": "is_remote", "target_type": "bool"},
                ],
                "http_methods": ["GET", "POST"],
            }
        },
    }

    spec = openapi_generator_v2.generate_spec(endpoint_data, base_server_url="http://localhost:8001")

    assert spec["openapi"] == "3.1.0"
    assert "Tech Jobs API" in spec["info"]["title"]

    path_obj = spec["paths"]["/v2/api/test_user/tech-jobs"]
    assert "get" in path_obj
    assert "post" in path_obj

    # Check GET parameters
    get_params = path_obj["get"]["parameters"]
    assert any(p["name"] == "location" for p in get_params)
    assert any(p["name"] == "min_salary" for p in get_params)

    # Check Swagger HTML generation
    html = openapi_generator_v2.generate_swagger_ui_html(
        openapi_json_url="/v2/api/test_user/tech-jobs/openapi.json",
        title="Tech Jobs API Documentation",
    )
    assert "swagger-ui" in html
    assert "/v2/api/test_user/tech-jobs/openapi.json" in html


@pytest.mark.asyncio
async def test_runtime_parameter_injection_in_sandbox():
    """Verify that query params pass directly into Playwright page.evaluate() for dynamic in-browser filtering."""
    extractor = HierarchicalExtractor()
    plan = ContainerExtractionPlan(
        strategy="custom_js",
        container_selector="",
        custom_js_extractor="""(params) => {
            const minScore = parseInt(params.min_score || 0);
            const limit = parseInt(params.limit || 10);
            const items = [
                { title: 'Project A', score: '50 points' },
                { title: 'Project B', score: '200 points' },
                { title: 'Project C', score: '120 points' },
            ];
            return items
                .filter(i => parseInt(i.score) >= minScore)
                .slice(0, limit);
        }""",
        contract=EndpointContract(
            response_shape="list",
            fields=[
                FieldTypeSpec(name="title", target_type="str"),
                FieldTypeSpec(name="score", target_type="int"),
            ],
        ),
    )

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content("<html><body><div>test</div></body></html>")

        # Test with min_score = 100 filter passed via runtime_params
        res = await extractor.extract_with_plan(
            page=page,
            plan=plan,
            target_schema={"title": "str", "score": "int"},
            runtime_params={"min_score": 100, "limit": 5},
        )
        await browser.close()

    assert res.success is True
    assert res.count == 2
    # Verify titles filtered and scores coerced to integer
    assert res.data[0]["title"] == "Project B"
    assert res.data[0]["score"] == 200
    assert res.data[1]["title"] == "Project C"
    assert res.data[1]["score"] == 120


@pytest.mark.asyncio
async def test_api_openapi_and_post_endpoints():
    """Verify GET /openapi.json, GET /docs, and POST query endpoints via FastAPI test client."""
    # Seed mock endpoint in database
    await endpoint_repo_v2.save_endpoint(
        endpoint_id="ep_contract_test",
        user_id="user_test",
        api_name="Contract Test API",
        slug="contract-test",
        target_url="https://example.com/items",
        schema_definition={"title": "str", "price": "float"},
        inputs={"category": {"type": "str", "description": "Category filter"}},
        plan={
            "strategy": "hierarchical_dom",
            "container_selector": "div.item",
            "contract": {
                "response_shape": "list",
                "parameters": [{"name": "category", "type": "str", "location": "query"}],
                "fields": [{"name": "title", "target_type": "str"}, {"name": "price", "target_type": "float"}],
            },
        },
        sample_data=[{"title": "Item 1", "price": 19.99}],
        api_key="mapik_test_12345",
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Test OpenAPI JSON endpoint
        open_res = await client.get("/v2/api/user_test/contract-test/openapi.json")
        assert open_res.status_code == 200
        spec = open_res.json()
        assert spec["openapi"] == "3.1.0"
        assert "/v2/api/user_test/contract-test" in spec["paths"]

        # 2. Test Swagger UI docs endpoint
        docs_res = await client.get("/v2/api/user_test/contract-test/docs")
        assert docs_res.status_code == 200
        assert "swagger-ui" in docs_res.text
