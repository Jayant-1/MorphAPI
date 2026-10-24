"""
Tests for MorphAPI Model Context Protocol (MCP) Server.
Verifies tool discovery, input validation, execution parity, and safety boundaries.
"""

import json
import pytest
from unittest.mock import AsyncMock, patch

from morphapi.mcp.server import mcp_server
from morphapi.db.repository import EndpointRepository, VersionRepository, JobRepository
from morphapi.schemas.contracts import ExtractionResult, ValidationResult
from morphapi.schemas.endpoint import EndpointStatus


@pytest.fixture
def clean_db(tmp_path, monkeypatch):
    test_db = str(tmp_path / "test_mcp.db")
    monkeypatch.setattr("morphapi.config.settings.db_path", test_db)
    from morphapi.services.endpoint_service import endpoint_service
    from morphapi.services.extraction_service import shared_extraction_service
    endpoint_service.endpoint_repo.db_path = test_db
    endpoint_service.version_repo.db_path = test_db
    if endpoint_service.auditor and endpoint_service.auditor.repo:
        endpoint_service.auditor.repo.db_path = test_db
    shared_extraction_service.endpoint_repo.db_path = test_db
    shared_extraction_service.version_repo.db_path = test_db

    import asyncio
    from morphapi.db.migrations import run_migrations
    asyncio.run(run_migrations(db_path=test_db))
    return test_db


@pytest.mark.asyncio
async def test_mcp_tools_registration():
    """Verify that all 6 required MCP tools are registered with schemas."""
    tools = await mcp_server.list_tools()
    tool_names = [t.name for t in tools]
    
    assert "list_integrations" in tool_names
    assert "get_integration_details" in tool_names
    assert "execute_integration" in tool_names
    assert "create_web_api" in tool_names
    assert "get_healing_status" in tool_names
    assert "request_repair" in tool_names
    assert len(tools) == 6


@pytest.mark.asyncio
async def test_mcp_create_web_api_and_details(clean_db):
    """Test creating a web API draft and fetching its details via MCP tools."""
    # Create draft
    create_res = await mcp_server.call_tool(
        "create_web_api",
        {
            "name": "E-Commerce Scraper",
            "slug": "mcp-ecommerce-test",
            "target_url": "https://example.com/products",
            "schema_definition": {"title": "str", "price": "float"},
        },
    )
    assert not create_res.is_error
    payload = json.loads(create_res.content[0].text)
    assert payload["status"] == "DRAFT"
    endpoint_id = payload["endpoint_id"]
    assert endpoint_id.startswith("ep_")

    # List integrations
    list_res = await mcp_server.call_tool("list_integrations", {})
    integrations = json.loads(list_res.content[0].text)
    assert len(integrations) == 1
    assert integrations[0]["endpoint_id"] == endpoint_id

    # Get details
    detail_res = await mcp_server.call_tool("get_integration_details", {"endpoint_id": endpoint_id})
    details = json.loads(detail_res.content[0].text)
    assert details["endpoint_id"] == endpoint_id
    assert details["status"] == "DRAFT"
    assert "https://example.com/products" in details["target_url"]


@pytest.mark.asyncio
async def test_mcp_execute_integration_blocks_unverified(clean_db):
    """Verify that execute_integration refuses to execute DRAFT or non-ACTIVE endpoints."""
    # Create draft
    create_res = await mcp_server.call_tool(
        "create_web_api",
        {
            "name": "Unverified Target",
            "slug": "unverified-ep",
            "target_url": "https://example.com/unverified",
            "schema_definition": {"title": "str"},
        },
    )
    endpoint_id = json.loads(create_res.content[0].text)["endpoint_id"]

    # Attempt execute
    exec_res = await mcp_server.call_tool("execute_integration", {"endpoint_id": endpoint_id})
    res_data = json.loads(exec_res.content[0].text)
    assert "error" in res_data
    assert "not ACTIVE" in res_data["error"]
    assert res_data["status"] == "DRAFT"


@pytest.mark.asyncio
async def test_mcp_execute_integration_active_success(clean_db):
    """Verify executing an active integration succeeds and returns structured data."""
    from morphapi.services.endpoint_service import endpoint_service
    from morphapi.schemas.endpoint import CandidateSubmitRequest, CandidateVerifyRequest

    # Create draft
    create_res = await mcp_server.call_tool(
        "create_web_api",
        {
            "name": "Active Scraper",
            "slug": "active-ep",
            "target_url": "https://example.com/items",
            "schema_definition": {"title": "str", "price": "float"},
        },
    )
    endpoint_id = json.loads(create_res.content[0].text)["endpoint_id"]

    # Submit, verify, and activate candidate
    cand_ver = await endpoint_service.submit_candidate(
        endpoint_id,
        CandidateSubmitRequest(selector_map={"title": ".item-title", "price": ".item-price"}),
    )
    await endpoint_service.verify_candidate(
        endpoint_id,
        cand_ver.version_id,
        CandidateVerifyRequest(sample_data={"title": "Test Title", "price": 10.5}),
    )
    await endpoint_service.activate_version(endpoint_id, cand_ver.version_id)

    # Mock browser extraction
    mock_extraction = ExtractionResult(
        success=True,
        target_url="https://example.com/items",
        data=[{"title": "Book A", "price": 19.99}],
        latency_ms=45,
    )

    with patch("morphapi.services.extraction_service.BrowserExtractor.extract", new=AsyncMock(return_value=mock_extraction)):
        exec_res = await mcp_server.call_tool("execute_integration", {"endpoint_id": endpoint_id})
        assert not exec_res.is_error
        res_data = json.loads(exec_res.content[0].text)
        assert res_data["endpoint_id"] == endpoint_id
        assert res_data["data"] == [{"title": "Book A", "price": 19.99}]
        assert res_data["execution_path"] == "FAST_PATH"


@pytest.mark.asyncio
async def test_mcp_get_healing_status(clean_db):
    """Verify reading healing job status via MCP."""
    ep_repo = EndpointRepository()
    ep = await ep_repo.create_endpoint(
        name="Target for Healing",
        target_url="https://example.com/target",
        schema_definition={"field1": "str"},
    )
    endpoint_id = ep["endpoint_id"]

    job_repo = JobRepository()
    job = await job_repo.create_job(
        endpoint_id=endpoint_id,
        job_type="healing",
        max_attempts=3,
    )
    job_id = job["job_id"]
    await job_repo.update_job_status(job_id, status="RUNNING", attempt_count=1)

    # Query status
    status_res = await mcp_server.call_tool("get_healing_status", {"job_id": job_id})
    assert not status_res.is_error
    data = json.loads(status_res.content[0].text)
    assert data["job_id"] == job_id
    assert data["endpoint_id"] == endpoint_id
    assert data["status"] == "RUNNING"


@pytest.mark.asyncio
async def test_mcp_request_repair(clean_db):
    """Verify triggering repair via MCP request_repair tool."""
    from morphapi.services.endpoint_service import endpoint_service
    from morphapi.schemas.endpoint import CandidateSubmitRequest, CandidateVerifyRequest

    create_res = await mcp_server.call_tool(
        "create_web_api",
        {
            "name": "Repair Target",
            "slug": "repair-target",
            "target_url": "https://example.com/repair",
            "schema_definition": {"title": "str"},
        },
    )
    endpoint_id = json.loads(create_res.content[0].text)["endpoint_id"]

    cand_ver = await endpoint_service.submit_candidate(
        endpoint_id,
        CandidateSubmitRequest(selector_map={"title": ".old-title"}),
    )
    await endpoint_service.verify_candidate(
        endpoint_id,
        cand_ver.version_id,
        CandidateVerifyRequest(sample_data={"title": "Old"}),
    )
    await endpoint_service.activate_version(endpoint_id, cand_ver.version_id)

    with patch("morphapi.mcp.server.healing_service.heal_endpoint", new=AsyncMock(return_value={"version": 2, "new_selectors": {"title": ".new-title"}})):
        repair_res = await mcp_server.call_tool("request_repair", {"endpoint_id": endpoint_id})
        assert not repair_res.is_error
        res_data = json.loads(repair_res.content[0].text)
        assert res_data["status"] == "REPAIRED"
        assert res_data["new_version"] == 2
        assert res_data["selectors"] == {"title": ".new-title"}
