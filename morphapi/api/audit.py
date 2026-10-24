"""
MorphAPI Audit Trail Routes
Provides append-only historical audit events for governance and compliance.
"""

from fastapi import APIRouter, Query, status
from morphapi.schemas.audit import AuditListResponse
from morphapi.services.audit_service import audit_service

router = APIRouter(prefix="/api/v1/endpoints", tags=["Audit"])


@router.get("/{endpoint_id}/audit", response_model=AuditListResponse, status_code=status.HTTP_200_OK)
async def get_endpoint_audit_trail(
    endpoint_id: str,
    limit: int = Query(default=50, ge=1, le=200),
):
    """
    Retrieves immutable audit events recorded for a specific endpoint.
    """
    return await audit_service.get_audit_trail(endpoint_id, limit=limit)
