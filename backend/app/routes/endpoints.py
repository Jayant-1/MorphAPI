"""
MorphAPI Endpoint Registry Routes
Conforms strictly to docs/SHARED_CONTRACT.md
"""

import logging
from fastapi import APIRouter, HTTPException, status
from backend.app.database import (
    register_endpoint,
    get_endpoint,
    list_endpoints,
    get_healing_logs,
)
from backend.app.models.contracts import (
    EndpointRegisterRequest,
    ErrorResponse,
)

logger = logging.getLogger("morphapi.routes.endpoints")
router = APIRouter(prefix="/api/v1/endpoints", tags=["Endpoints"])


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Endpoint successfully registered"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def register_new_endpoint(payload: EndpointRegisterRequest):
    """
    Registers a new target endpoint, schema definition, and optional initial selectors.
    """
    try:
        endpoint = await register_endpoint(
            endpoint_id=payload.endpoint_id,
            name=payload.name,
            target_url=str(payload.target_url),
            schema_definition=payload.schema_definition,
            initial_selectors=payload.initial_selectors,
        )
        return endpoint
    except Exception as e:
        logger.exception(f"Error registering endpoint {payload.endpoint_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}",
        )


@router.get("", status_code=status.HTTP_200_OK)
async def get_all_endpoints():
    """
    Lists all registered endpoints with their current health status and versions.
    """
    return await list_endpoints()


@router.get("/{endpoint_id}", status_code=status.HTTP_200_OK)
async def get_single_endpoint(endpoint_id: str):
    """
    Retrieves configuration, active selectors, and lifecycle status for an endpoint.
    """
    endpoint = await get_endpoint(endpoint_id)
    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Endpoint '{endpoint_id}' was not found.",
        )
    return endpoint


@router.get("/{endpoint_id}/healing-logs", status_code=status.HTTP_200_OK)
async def get_endpoint_healing_logs(endpoint_id: str, limit: int = 50):
    """
    Retrieves the historical audit trail of self-healing events for an endpoint.
    """
    endpoint = await get_endpoint(endpoint_id)
    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Endpoint '{endpoint_id}' was not found.",
        )
    logs = await get_healing_logs(endpoint_id, limit=limit)
    return logs
