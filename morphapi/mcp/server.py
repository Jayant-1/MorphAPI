"""
MorphAPI Model Context Protocol (MCP) Server
Exposes verified Web-to-API endpoints as AI agent tools via MCP v2 SDK.
Shares the single deterministic extraction service and endpoint registry with REST.
"""

import json
import logging
from typing import Any
from mcp.server.mcpserver import MCPServer
from pydantic import BaseModel, Field

from morphapi.services.endpoint_service import endpoint_service
from morphapi.services.extraction_service import shared_extraction_service
from morphapi.services.healing_service import HealingService
from morphapi.db.repository import EndpointRepository, JobRepository, VersionRepository
from morphapi.schemas.endpoint import EndpointCreateRequest

logger = logging.getLogger("morphapi.mcp")

# Initialize MCP Server
mcp_server = MCPServer("MorphAPI Gateway")
job_repo = JobRepository()
healing_service = HealingService()


# --- Tool 1: list_integrations ---
@mcp_server.tool()
async def list_integrations(tenant_id: str = "default_tenant") -> str:
    """
    Lists active and verified integrations available to the caller.
    """
    try:
        endpoints = await endpoint_service.list_endpoints(tenant_id=tenant_id)
        result = [
            {
                "endpoint_id": ep.endpoint_id,
                "name": ep.name,
                "status": ep.status.value,
                "target_url": ep.target_url,
                "schema": ep.schema_definition,
                "active_version": ep.active_version_id,
            }
            for ep in endpoints
        ]
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Failed to list integrations: {str(e)}"})


# --- Tool 2: get_integration_details ---
@mcp_server.tool()
async def get_integration_details(endpoint_id: str, tenant_id: str = "default_tenant") -> str:
    """
    Returns an integration's description, schema, allowed URL scope, and lifecycle status.
    """
    try:
        ep = await endpoint_service.get_endpoint(endpoint_id, tenant_id=tenant_id)
        return json.dumps({
            "endpoint_id": ep.endpoint_id,
            "name": ep.name,
            "status": ep.status.value,
            "target_url": ep.target_url,
            "output_schema": ep.schema_definition,
            "allowed_url_scope": ep.allowed_url_scope,
            "active_version_id": ep.active_version_id,
            "created_at": ep.created_at,
            "updated_at": ep.updated_at,
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Failed to retrieve integration details: {str(e)}"})


# --- Tool 3: execute_integration ---
@mcp_server.tool()
async def execute_integration(endpoint_id: str, tenant_id: str = "default_tenant") -> str:
    """
    Executes an active, verified integration and returns structured extracted data.
    Uses identical zero-token Fast Path and shared extraction pipeline as REST.
    """
    try:
        # Check active status first
        ep = await endpoint_service.get_endpoint(endpoint_id, tenant_id=tenant_id)
        if ep.status.value != "ACTIVE":
            return json.dumps({
                "error": f"Integration '{endpoint_id}' is not ACTIVE (current status: {ep.status.value}). Only active integrations can be executed.",
                "status": ep.status.value,
            })

        response = await shared_extraction_service.extract_endpoint(
            endpoint_id=endpoint_id,
            tenant_id=tenant_id,
        )
        return json.dumps({
            "endpoint_id": response.endpoint_id,
            "data": response.data,
            "execution_path": response.execution_path,
            "latency_ms": response.latency_ms,
            "fetched_at": response.fetched_at,
            "config_version": response.config_version,
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Execution failed: {str(e)}"})


# --- Tool 4: create_web_api ---
@mcp_server.tool()
async def create_web_api(
    name: str,
    target_url: str,
    schema_definition: dict[str, str],
    slug: str | None = None,
    tenant_id: str = "default_tenant",
) -> str:
    """
    Starts creating a new Web-to-API integration from a target URL and schema.
    Creates a draft configuration awaiting backend verification before activation.
    """
    try:
        req = EndpointCreateRequest(
            name=name,
            slug=slug,
            target_url=target_url,
            schema_definition=schema_definition,
        )
        created = await endpoint_service.create_endpoint_draft(req, tenant_id=tenant_id)
        return json.dumps({
            "message": "Draft integration created. Ready for discovery and verification.",
            "endpoint_id": created.endpoint_id,
            "status": created.status.value,
            "target_url": created.target_url,
            "schema": created.schema_definition,
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Failed to create web API draft: {str(e)}"})


# --- Tool 5: get_healing_status ---
@mcp_server.tool()
async def get_healing_status(job_id: str) -> str:
    """
    Returns the status and diagnostic history of an agentic healing attempt.
    """
    try:
        job = await job_repo.get_job(job_id)
        if not job:
            return json.dumps({"error": f"Job '{job_id}' not found."})
        return json.dumps({
            "job_id": job["job_id"],
            "endpoint_id": job["endpoint_id"],
            "status": job["status"],
            "attempts": f"{job['attempt_count']}/{job['max_attempts']}",
            "failure_reason": job["failure_reason"],
            "result_summary": job["result_summary"],
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Failed to retrieve healing status: {str(e)}"})


# --- Tool 6: request_repair ---
@mcp_server.tool()
async def request_repair(endpoint_id: str, tenant_id: str = "default_tenant") -> str:
    """
    Initiates a bounded self-healing workflow for an integration that needs repair.
    """
    try:
        ep = await endpoint_service.get_endpoint(endpoint_id, tenant_id=tenant_id)
        # Fetch active or last known selectors
        v_repo = VersionRepository()
        version = await v_repo.get_version(ep.active_version_id) if ep.active_version_id else None
        current_selectors = (version.get("selector_map") or version.get("selectors") or {}) if version else {}
        current_v_num = version["version_number"] if version else 1

        heal_res = await healing_service.heal_endpoint(
            endpoint_id=endpoint_id,
            target_url=ep.target_url,
            schema_definition=ep.schema_definition,
            current_selectors=current_selectors,
            current_version=current_v_num,
            failure_reason="Explicit repair requested via MCP tool",
        )
        return json.dumps({
            "status": "REPAIRED",
            "new_version": heal_res.get("version"),
            "selectors": heal_res.get("new_selectors"),
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Repair request failed: {str(e)}"})
