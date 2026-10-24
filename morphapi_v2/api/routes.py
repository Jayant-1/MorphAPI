"""
API Routes for MorphAPI V2
"""

from typing import Any
from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from morphapi_v2.schemas.models import EndpointV2CreateRequest, EndpointV2Response
from morphapi_v2.engine.gateway_engine import gateway_engine_v2
from morphapi_v2.engine.openapi_generator import openapi_generator_v2
from morphapi_v2.db.repository import endpoint_repo_v2
from morphapi_v2.demo.mock_store import (
    render_mock_store_html,
    toggle_mode,
    set_mode,
    get_current_mode,
)

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
@router.post(
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
    Accepts query parameters and optional POST JSON body to parameterize extraction.
    """
    query_params = dict(request.query_params)

    # Merge JSON body params if POST request
    if request.method == "POST":
        try:
            body = await request.json()
            if isinstance(body, dict):
                query_params.update(body)
        except Exception:
            pass

    try:
        data = await gateway_engine_v2.execute_query(
            user_id=user_id,
            slug=slug,
            query_params=query_params,
        )
        if isinstance(data, dict):
            return data
        return {
            "endpoint": f"/v2/api/{user_id}/{slug}",
            "count": len(data),
            "data": data,
        }
    except KeyError as ke:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ke))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/api/{user_id}/{slug}/openapi.json",
    status_code=status.HTTP_200_OK,
)
async def get_endpoint_openapi(user_id: str, slug: str, request: Request):
    """
    Returns dynamic OpenAPI 3.1 schema specifically tailored for this synthesized endpoint.
    """
    endpoint = await endpoint_repo_v2.get_endpoint(user_id=user_id, slug=slug)
    if not endpoint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Endpoint '{slug}' not found")

    base_url = str(request.base_url).rstrip("/")
    return openapi_generator_v2.generate_spec(endpoint, base_server_url=base_url)


@router.get(
    "/api/{user_id}/{slug}/docs",
    response_class=HTMLResponse,
    status_code=status.HTTP_200_OK,
)
async def get_endpoint_docs(user_id: str, slug: str):
    """
    Interactive Swagger UI documentation page for this synthesized endpoint.
    """
    endpoint = await endpoint_repo_v2.get_endpoint(user_id=user_id, slug=slug)
    if not endpoint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Endpoint '{slug}' not found")

    openapi_json_url = f"/v2/api/{user_id}/{slug}/openapi.json"
    return openapi_generator_v2.generate_swagger_ui_html(
        openapi_json_url=openapi_json_url,
        title=f"{endpoint.get('api_name', slug).title()} Documentation",
    )


@router.get("/endpoints", status_code=status.HTTP_200_OK)
async def list_endpoints():
    return await endpoint_repo_v2.list_endpoints()


@router.get("/health", status_code=status.HTTP_200_OK)
async def health():
    return {"status": "ok", "version": "2.0.0"}


@router.get("/demo/mock-store", response_class=HTMLResponse)
async def get_mock_store(mode: str | None = None):
    """
    Renders simulated mock store with toggleable UI layout (V1 card grid vs V2 multi-row sibling layout).
    """
    if mode:
        set_mode(mode)
    return render_mock_store_html(mode)


@router.post("/demo/mock-store/toggle")
async def toggle_mock_store():
    """Toggles mock store UI layout between V1 and V2."""
    new_mode = toggle_mode()
    return {"mode": new_mode, "message": f"Mock store UI mutated to {new_mode}"}


@router.post("/demo/mock-store/set-mode")
async def set_mock_store_mode(mode: str = "v1"):
    """Sets mock store UI layout explicitly to v1 or v2."""
    set_mode(mode)
    return {"mode": get_current_mode(), "message": f"Mock store UI set to {get_current_mode()}"}
