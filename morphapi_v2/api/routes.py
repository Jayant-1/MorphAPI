"""
API Routes for MorphAPI V2
"""

from typing import Any
from fastapi import APIRouter, HTTPException, Query, Request, status
from morphapi_v2.schemas.models import EndpointV2CreateRequest, EndpointV2Response
from morphapi_v2.engine.gateway_engine import gateway_engine_v2
from morphapi_v2.db.repository import endpoint_repo_v2

router = APIRouter(prefix="/v2", tags=["MorphAPI V2"])


@router.post(
    "/endpoints/synthesize",
    response_model=EndpointV2Response,
    status_code=status.HTTP_201_CREATED,
)
async def synthesize_endpoint(payload: EndpointV2CreateRequest):
    """
    Synthesizes a new production-ready API endpoint from natural language intent or target URL.
    Employs network API sniffing, DOM cluster analysis, hierarchical extraction, and semantic validation.
    """
    try:
        return await gateway_engine_v2.create_endpoint(payload)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/api/{user_id}/{slug}",
    status_code=status.HTTP_200_OK,
)
async def query_endpoint(
    user_id: str,
    slug: str,
    request: Request,
):
    """
    Client dynamic query endpoint: executes live extraction using verified active plan.
    Accepts query parameters (e.g. ?batch=W25) to parameterize target URL.
    """
    query_params = dict(request.query_params)
    try:
        data = await gateway_engine_v2.execute_query(
            user_id=user_id,
            slug=slug,
            query_params=query_params,
        )
        return {
            "endpoint": f"/v2/api/{user_id}/{slug}",
            "count": len(data),
            "data": data,
        }
    except KeyError as ke:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ke))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/endpoints", status_code=status.HTTP_200_OK)
async def list_endpoints():
    return await endpoint_repo_v2.list_endpoints()


@router.get("/health", status_code=status.HTTP_200_OK)
async def health():
    return {"status": "ok", "version": "2.0.0"}
