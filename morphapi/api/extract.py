"""
MorphAPI Extraction REST Routes
Unified endpoint for browser-backed deterministic extraction.
Supports tenant/user scoped dynamic paths (/v1/api/{user_id}/{api_name})
and dynamic query parameter forwarding to target URLs.
"""

from typing import Any
from fastapi import APIRouter, Body, Header, Request, status
from morphapi.observability.correlation import get_correlation_id
from morphapi.schemas.contracts import ExtractionResponse
from morphapi.schemas.errors import ErrorResponse
from morphapi.services.extraction_service import shared_extraction_service

router = APIRouter(tags=["Extraction"])


@router.get(
    "/v1/api/{user_id}/{api_name}",
    response_model=ExtractionResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Extraction completed successfully (FAST_PATH or SELF_HEALED)"},
        404: {"model": ErrorResponse, "description": "Endpoint not found"},
        422: {"model": ErrorResponse, "description": "Candidate not verified or schema invalid"},
        502: {"model": ErrorResponse, "description": "Autonomous extraction/healing failed"},
        504: {"model": ErrorResponse, "description": "Browser timeout"},
    },
)
@router.get(
    "/api/v1/{user_id}/{api_name}",
    response_model=ExtractionResponse,
    status_code=status.HTTP_200_OK,
)
@router.get(
    "/api/v1/extract/{endpoint_id}",
    response_model=ExtractionResponse,
    status_code=status.HTTP_200_OK,
)
async def extract_get(
    request: Request,
    endpoint_id: str | None = None,
    user_id: str | None = None,
    api_name: str | None = None,
    limit: int | None = None,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_correlation_id: str | None = Header(default=None, alias="X-Correlation-ID"),
):
    """
    Executes extraction for an active endpoint via GET.
    Accepts arbitrary dynamic query parameters (e.g. ?year=2025&batch=W25) to parameterize target URL.
    Zero-token Fast Path executes first; self-healing triggers only on failure.
    """
    req_id = x_correlation_id or get_correlation_id()
    target_id = api_name or endpoint_id or ""
    effective_tenant = user_id or x_tenant_id or "default_tenant"

    # Extract dynamic query params excluding system query args
    dynamic_params = {k: v for k, v in request.query_params.items() if k not in ("limit", "x_api_key", "tenant_id")}
    resp = await shared_extraction_service.extract_endpoint(
        endpoint_id=target_id,
        tenant_id=effective_tenant,
        request_id=req_id,
        params=dynamic_params,
    )
    if limit is not None and isinstance(resp.data, list):
        resp.data = resp.data[:limit]
    return resp


@router.post(
    "/v1/api/{user_id}/{api_name}",
    response_model=ExtractionResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Extraction completed successfully (FAST_PATH or SELF_HEALED)"},
        404: {"model": ErrorResponse, "description": "Endpoint not found"},
        422: {"model": ErrorResponse, "description": "Candidate not verified or schema invalid"},
        502: {"model": ErrorResponse, "description": "Autonomous extraction/healing failed"},
        504: {"model": ErrorResponse, "description": "Browser timeout"},
    },
)
@router.post(
    "/api/v1/{user_id}/{api_name}",
    response_model=ExtractionResponse,
    status_code=status.HTTP_200_OK,
)
@router.post(
    "/api/v1/extract/{endpoint_id}",
    response_model=ExtractionResponse,
    status_code=status.HTTP_200_OK,
)
async def extract_post(
    request: Request,
    endpoint_id: str | None = None,
    user_id: str | None = None,
    api_name: str | None = None,
    payload: dict[str, Any] | None = Body(default=None),
    limit: int | None = None,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_correlation_id: str | None = Header(default=None, alias="X-Correlation-ID"),
):
    """
    Executes extraction for an active endpoint via POST.
    Accepts JSON body or query params to dynamically parameterize the target URL.
    """
    req_id = x_correlation_id or get_correlation_id()
    target_id = api_name or endpoint_id or ""
    effective_tenant = user_id or x_tenant_id or "default_tenant"

    dynamic_params = {k: v for k, v in request.query_params.items() if k not in ("limit", "x_api_key", "tenant_id")}
    if payload and isinstance(payload, dict):
        dynamic_params.update(payload)

    resp = await shared_extraction_service.extract_endpoint(
        endpoint_id=target_id,
        tenant_id=effective_tenant,
        request_id=req_id,
        params=dynamic_params,
    )
    if limit is not None and isinstance(resp.data, list):
        resp.data = resp.data[:limit]
    return resp
