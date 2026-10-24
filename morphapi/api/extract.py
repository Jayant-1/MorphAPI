"""
MorphAPI Extraction REST Routes
Unified endpoint for browser-backed deterministic extraction.
Invokes shared extraction service (identical logic to MCP tool).
"""

from fastapi import APIRouter, Header, status
from morphapi.observability.correlation import get_correlation_id
from morphapi.schemas.contracts import ExtractionResponse
from morphapi.schemas.errors import ErrorResponse
from morphapi.services.extraction_service import shared_extraction_service

router = APIRouter(prefix="/api/v1/extract", tags=["Extraction"])


@router.get(
    "/{endpoint_id}",
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
async def extract_get(
    endpoint_id: str,
    x_tenant_id: str | None = Header(default="default_tenant", alias="X-Tenant-ID"),
    x_correlation_id: str | None = Header(default=None, alias="X-Correlation-ID"),
):
    """
    Executes extraction for an active endpoint via GET.
    Zero-token Fast Path executes first; self-healing triggers only on failure.
    """
    req_id = x_correlation_id or get_correlation_id()
    return await shared_extraction_service.extract_endpoint(
        endpoint_id=endpoint_id,
        tenant_id=x_tenant_id or "default_tenant",
        request_id=req_id,
    )


@router.post(
    "/{endpoint_id}",
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
async def extract_post(
    endpoint_id: str,
    x_tenant_id: str | None = Header(default="default_tenant", alias="X-Tenant-ID"),
    x_correlation_id: str | None = Header(default=None, alias="X-Correlation-ID"),
):
    """
    Executes extraction for an active endpoint via POST.
    """
    req_id = x_correlation_id or get_correlation_id()
    return await shared_extraction_service.extract_endpoint(
        endpoint_id=endpoint_id,
        tenant_id=x_tenant_id or "default_tenant",
        request_id=req_id,
    )
