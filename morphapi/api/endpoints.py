"""
MorphAPI Endpoint Lifecycle Routes
Full CRUD, candidate submission, deterministic verification, atomic activation, and rollback.
"""

from fastapi import APIRouter, Header, Response, status
from morphapi.schemas.endpoint import (
    CandidateSubmitRequest,
    CandidateVerifyRequest,
    CandidateVerifyResponse,
    EndpointActivateRequest,
    EndpointCreateRequest,
    EndpointResponse,
    EndpointRollbackRequest,
    EndpointVersionResponse,
)
from morphapi.schemas.errors import ErrorResponse
from morphapi.services.endpoint_service import endpoint_service

router = APIRouter(prefix="/api/v1/endpoints", tags=["Endpoints"])


@router.post(
    "",
    response_model=EndpointResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Draft endpoint created successfully"},
        400: {"model": ErrorResponse, "description": "Invalid endpoint parameters"},
        422: {"model": ErrorResponse, "description": "Schema validation failure"},
    },
)
async def create_endpoint_draft(
    payload: EndpointCreateRequest,
    x_tenant_id: str | None = Header(default="default_tenant", alias="X-Tenant-ID"),
):
    """
    Creates a new draft endpoint configuration. Does NOT activate the endpoint.
    """
    return await endpoint_service.create_endpoint_draft(
        request=payload,
        tenant_id=x_tenant_id or "default_tenant",
    )


@router.get("", response_model=list[EndpointResponse], status_code=status.HTTP_200_OK)
async def list_endpoints(
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    """
    Lists registered endpoints for the active tenant.
    """
    return await endpoint_service.list_endpoints(tenant_id=x_tenant_id)


@router.get("/{endpoint_id}", response_model=EndpointResponse, status_code=status.HTTP_200_OK)
async def get_endpoint(
    endpoint_id: str,
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
):
    """
    Retrieves configuration and status for a specific endpoint.
    """
    return await endpoint_service.get_endpoint(endpoint_id, tenant_id=x_tenant_id)


@router.get("/{endpoint_id}/versions", response_model=list[EndpointVersionResponse], status_code=status.HTTP_200_OK)
async def list_versions(endpoint_id: str):
    """
    Lists configuration version history for an endpoint.
    """
    return await endpoint_service.list_versions(endpoint_id)


@router.get("/{endpoint_id}/versions/{version_id}", response_model=EndpointVersionResponse, status_code=status.HTTP_200_OK)
async def get_version(endpoint_id: str, version_id: str):
    """
    Retrieves details for a specific configuration version.
    """
    return await endpoint_service.get_version(endpoint_id, version_id)


@router.post("/{endpoint_id}/candidates", response_model=EndpointVersionResponse, status_code=status.HTTP_201_CREATED)
async def submit_candidate(
    endpoint_id: str,
    payload: CandidateSubmitRequest,
    x_tenant_id: str | None = Header(default="default_tenant", alias="X-Tenant-ID"),
):
    """
    Submits a proposed candidate selector map. Stores it as an unverified CANDIDATE version.
    Does not activate the configuration.
    """
    return await endpoint_service.submit_candidate(
        endpoint_id=endpoint_id,
        request=payload,
        tenant_id=x_tenant_id or "default_tenant",
    )


@router.post(
    "/{endpoint_id}/candidates/{version_id}/verify",
    response_model=CandidateVerifyResponse,
    status_code=status.HTTP_200_OK,
)
async def verify_candidate(
    endpoint_id: str,
    version_id: str,
    payload: CandidateVerifyRequest | None = None,
    x_tenant_id: str | None = Header(default="default_tenant", alias="X-Tenant-ID"),
):
    """
    Runs deterministic backend verification on a candidate configuration.
    Executes live selector test and deterministic schema validation.
    Marks version as 'VERIFIED' only if both pass.
    """
    return await endpoint_service.verify_candidate(
        endpoint_id=endpoint_id,
        version_id=version_id,
        request=payload,
        tenant_id=x_tenant_id or "default_tenant",
    )


@router.post(
    "/{endpoint_id}/activate",
    response_model=EndpointResponse,
    status_code=status.HTTP_200_OK,
)
async def activate_version(
    endpoint_id: str,
    payload: EndpointActivateRequest,
    x_tenant_id: str | None = Header(default="default_tenant", alias="X-Tenant-ID"),
):
    """
    Atomic backend-controlled promotion of a verified version to ACTIVE.
    Rejects activation if version is not in VERIFIED status.
    """
    endpoint, _ = await endpoint_service.activate_version(
        endpoint_id=endpoint_id,
        version_id=payload.version_id,
        approval_id=payload.approval_id,
        tenant_id=x_tenant_id or "default_tenant",
    )
    return endpoint


@router.post(
    "/{endpoint_id}/rollback",
    response_model=EndpointResponse,
    status_code=status.HTTP_200_OK,
)
async def rollback_to_last_known_good(
    endpoint_id: str,
    payload: EndpointRollbackRequest | None = None,
    x_tenant_id: str | None = Header(default="default_tenant", alias="X-Tenant-ID"),
):
    """
    Atomically rolls back the active configuration to last known good version.
    """
    endpoint, _ = await endpoint_service.rollback(
        endpoint_id=endpoint_id,
        reason=(payload and payload.reason) or "Manual rollback",
        tenant_id=x_tenant_id or "default_tenant",
    )
    return endpoint


from pydantic import BaseModel, Field


class GenerateEndpointPromptRequest(BaseModel):
    prompt: str = Field(
        ...,
        description="Natural language prompt describing the web API to create",
        examples=["Extract top 5 government resolution document links from https://sarthi.maharashtra.gov.in/en/government-resolution"],
    )
    target_url: str | None = Field(
        default=None,
        description="Optional target URL (if omitted, extracted from prompt)",
        examples=["https://sarthi.maharashtra.gov.in/en/government-resolution"],
    )
    name: str | None = Field(
        default=None,
        description="Optional display name for the endpoint",
        examples=["Sarthi Government Resolutions"],
    )


@router.post("/generate", status_code=status.HTTP_201_CREATED)
async def generate_endpoint_from_prompt(
    payload: GenerateEndpointPromptRequest,
    response: Response,
    x_tenant_id: str | None = Header(default="default_tenant", alias="X-Tenant-ID"),
):
    """
    Creates, discovers, verifies, and activates a Web-to-API endpoint from a natural language prompt.
    Returns the endpoint URL and API key ready for immediate extraction querying.
    """
    result = await endpoint_service.generate_endpoint_from_prompt(
        prompt=payload.prompt,
        target_url=payload.target_url,
        name=payload.name,
        tenant_id=x_tenant_id or "default_tenant",
    )
    if isinstance(result, dict) and result.get("status") == "BLOCKED":
        response.status_code = status.HTTP_403_FORBIDDEN
    return result
