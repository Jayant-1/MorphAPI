"""
MorphAPI Audit Service
Append-only facade for recording and retrieving audit events.
"""

from typing import Any
from morphapi.db.repository import AuditRepository
from morphapi.observability.correlation import get_correlation_id
from morphapi.observability.logging import logger
from morphapi.schemas.audit import AuditEvent, AuditEventType, AuditListResponse


class AuditService:
    def __init__(self, repo: AuditRepository | None = None):
        self.repo = repo or AuditRepository()

    async def record_event(
        self,
        action: AuditEventType | str,
        target_type: str,
        target_id: str,
        correlation_id: str | None = None,
        tenant_id: str = "default_tenant",
        actor: str = "system",
        details: dict[str, Any] | None = None,
    ) -> int:
        cid = correlation_id or get_correlation_id()
        action_str = action.value if isinstance(action, AuditEventType) else str(action)
        logger.info(f"Audit event: [{action_str}] on {target_type}:{target_id} by {actor}")
        return await self.repo.append_event(
            correlation_id=cid,
            tenant_id=tenant_id,
            actor=actor,
            action=action_str,
            target_type=target_type,
            target_id=target_id,
            details=details or {},
        )

    async def get_audit_trail(self, target_id: str, limit: int = 50) -> AuditListResponse:
        records = await self.repo.list_events_for_target(target_id, limit=limit)
        events = [
            AuditEvent(
                audit_id=r["audit_id"],
                correlation_id=r["correlation_id"],
                tenant_id=r["tenant_id"],
                actor=r["actor"],
                action=AuditEventType(r["action"]) if r["action"] in AuditEventType.__members__ else AuditEventType.ENDPOINT_UPDATED,
                target_type=r["target_type"],
                target_id=r["target_id"],
                details=r["details"],
                timestamp=r["timestamp"],
            )
            for r in records
        ]
        return AuditListResponse(endpoint_id=target_id, events=events, total_count=len(events))


audit_service = AuditService()
