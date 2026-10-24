"""
MorphAPI Extraction Routes
Executes unified dual-path extraction via shared orchestrator.
"""

import logging
from fastapi import APIRouter, HTTPException, status
from backend.app.models.contracts import ExtractionResponse, ErrorResponse
from backend.app.services.orchestrator import orchestrator_instance

logger = logging.getLogger("morphapi.routes.extract")
router = APIRouter(prefix="/api/v1/extract", tags=["Extraction"])


@router.get(
    "/{endpoint_id}",
    response_model=ExtractionResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Extraction succeeded via Fast Path or Self-Healing"},
        404: {"model": ErrorResponse, "description": "Endpoint not registered"},
        502: {"model": ErrorResponse, "description": "Unrecoverable selector failure"},
        504: {"model": ErrorResponse, "description": "Browser extraction timeout"},
    },
)
async def extract_endpoint_data(endpoint_id: str):
    """
    Triggers dual-path extraction for endpoint_id.
    Zero-token Fast Path executes first. If selectors drift, Self-Healing is invoked automatically.
    """
    try:
        response = await orchestrator_instance.execute_extraction(endpoint_id)
        return response
    except KeyError as ke:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "ENDPOINT_NOT_FOUND", "message": str(ke), "endpoint_id": endpoint_id},
        )
    except TimeoutError as te:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={"error_code": "EXTRACTION_TIMEOUT", "message": str(te), "endpoint_id": endpoint_id},
        )
    except Exception as e:
        logger.error(f"Extraction failed for '{endpoint_id}': {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error_code": "HEALING_FAILED",
                "message": f"Autonomous extraction and healing failed: {str(e)}",
                "endpoint_id": endpoint_id,
            },
        )
