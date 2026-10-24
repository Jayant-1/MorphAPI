"""
MorphAPI Isolated Database Repositories
Authoritative business records for tenants, endpoints, versions, jobs, and audit logs.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Optional
import aiosqlite

from morphapi.db.connection import get_db_connection
from morphapi.schemas.errors import FailureCode, MorphApiError


class CandidateNotVerifiedError(MorphApiError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(FailureCode.INVALID_CANDIDATE, message, details=details, retryable=False)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _format_endpoint(row: aiosqlite.Row) -> dict[str, Any]:
    return {
        "endpoint_id": row["endpoint_id"],
        "tenant_id": row["tenant_id"],
        "name": row["name"],
        "slug": row["slug"],
        "target_url": row["target_url"],
        "allowed_url_scope": json.loads(row["allowed_url_scope"]) if row["allowed_url_scope"] else [],
        "schema_definition": json.loads(row["schema_definition"]) if row["schema_definition"] else {},
        "field_descriptions": json.loads(row["field_descriptions"]) if row["field_descriptions"] else {},
        "extraction_hints": json.loads(row["extraction_hints"]) if row["extraction_hints"] else {},
        "freshness_seconds": row["freshness_seconds"],
        "status": row["status"],
        "active_version_id": row["active_version_id"],
        "last_known_good_version_id": row["last_known_good_version_id"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _format_version(row: aiosqlite.Row) -> dict[str, Any]:
    return {
        "version_id": row["version_id"],
        "endpoint_id": row["endpoint_id"],
        "version_number": row["version_number"],
        "schema_definition": json.loads(row["schema_definition"]) if row["schema_definition"] else {},
        "selector_map": json.loads(row["selector_map"]) if row["selector_map"] else {},
        "status": row["status"],
        "is_active": bool(row["is_active"]),
        "is_last_known_good": bool(row["is_last_known_good"]),
        "verification_result": json.loads(row["verification_result"]) if row["verification_result"] else None,
        "rationale": row["rationale"],
        "evidence_refs": json.loads(row["evidence_refs"]) if row["evidence_refs"] else [],
        "created_by": row["created_by"],
        "verified_at": row["verified_at"],
        "activated_at": row["activated_at"],
        "created_at": row["created_at"],
    }


def _format_job(row: aiosqlite.Row) -> dict[str, Any]:
    return {
        "job_id": row["job_id"],
        "endpoint_id": row["endpoint_id"],
        "tenant_id": row["tenant_id"],
        "job_type": row["job_type"],
        "workflow_thread_id": row["workflow_thread_id"],
        "status": row["status"],
        "attempt_count": row["attempt_count"],
        "max_attempts": row["max_attempts"],
        "deadline": row["deadline"],
        "failure_reason": row["failure_reason"],
        "result_summary": json.loads(row["result_summary"]) if row["result_summary"] else {},
        "clarification": json.loads(row["clarification"]) if row["clarification"] else None,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _format_audit(row: aiosqlite.Row) -> dict[str, Any]:
    return {
        "audit_id": row["audit_id"],
        "correlation_id": row["correlation_id"],
        "tenant_id": row["tenant_id"],
        "actor": row["actor"],
        "action": row["action"],
        "target_type": row["target_type"],
        "target_id": row["target_id"],
        "details": json.loads(row["details"]) if row["details"] else {},
        "timestamp": row["timestamp"],
    }


class EndpointRepository:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path

    async def create_endpoint(
        self,
        name: str,
        target_url: str,
        schema_definition: dict[str, str],
        slug: str | None = None,
        tenant_id: str = "default_tenant",
        allowed_url_scope: list[str] | None = None,
        field_descriptions: dict[str, str] | None = None,
        extraction_hints: dict[str, Any] | None = None,
        freshness_seconds: int = 300,
        initial_selectors: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        endpoint_id = f"ep_{uuid.uuid4().hex[:12]}"
        final_slug = slug or f"ep-{uuid.uuid4().hex[:8]}"
        initial_version_id = f"ver_{uuid.uuid4().hex[:12]}"
        now = _now()

        conn = await get_db_connection(self.db_path)
        try:
            # Create endpoint draft
            await conn.execute(
                """
                INSERT INTO endpoints (
                    endpoint_id, tenant_id, name, slug, target_url, allowed_url_scope,
                    schema_definition, field_descriptions, extraction_hints,
                    freshness_seconds, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'DRAFT', ?, ?)
                """,
                (
                    endpoint_id,
                    tenant_id,
                    name,
                    final_slug,
                    target_url,
                    json.dumps(allowed_url_scope or []),
                    json.dumps(schema_definition),
                    json.dumps(field_descriptions or {}),
                    json.dumps(extraction_hints or {}),
                    freshness_seconds,
                    now,
                    now,
                ),
            )

            # Create initial version draft (version 1)
            await conn.execute(
                """
                INSERT INTO endpoint_versions (
                    version_id, endpoint_id, version_number, schema_definition,
                    selector_map, status, is_active, is_last_known_good,
                    rationale, created_by, created_at
                ) VALUES (?, ?, 1, ?, ?, ?, 0, 0, ?, 'system', ?)
                """,
                (
                    initial_version_id,
                    endpoint_id,
                    json.dumps(schema_definition),
                    json.dumps(initial_selectors or {}),
                    "CANDIDATE" if initial_selectors else "DRAFT",
                    "Initial configuration proposal" if initial_selectors else "Initial draft schema",
                    now,
                ),
            )

            await conn.commit()

            cursor = await conn.execute("SELECT * FROM endpoints WHERE endpoint_id = ?", (endpoint_id,))
            row = await cursor.fetchone()
            return _format_endpoint(row)
        finally:
            await conn.close()

    async def get_endpoint(self, endpoint_id: str, tenant_id: str | None = None) -> Optional[dict[str, Any]]:
        conn = await get_db_connection(self.db_path)
        try:
            query = "SELECT * FROM endpoints WHERE endpoint_id = ?"
            params = [endpoint_id]
            if tenant_id:
                query += " AND tenant_id = ?"
                params.append(tenant_id)
            cursor = await conn.execute(query, tuple(params))
            row = await cursor.fetchone()
            return _format_endpoint(row) if row else None
        finally:
            await conn.close()

    async def get_endpoint_by_slug(self, slug: str, tenant_id: str | None = None) -> Optional[dict[str, Any]]:
        conn = await get_db_connection(self.db_path)
        try:
            query = "SELECT * FROM endpoints WHERE slug = ?"
            params = [slug]
            if tenant_id:
                query += " AND tenant_id = ?"
                params.append(tenant_id)
            cursor = await conn.execute(query, tuple(params))
            row = await cursor.fetchone()
            return _format_endpoint(row) if row else None
        finally:
            await conn.close()

    async def list_endpoints(self, tenant_id: str | None = None) -> list[dict[str, Any]]:
        conn = await get_db_connection(self.db_path)
        try:
            if tenant_id:
                cursor = await conn.execute(
                    "SELECT * FROM endpoints WHERE tenant_id = ? ORDER BY created_at DESC",
                    (tenant_id,),
                )
            else:
                cursor = await conn.execute("SELECT * FROM endpoints ORDER BY created_at DESC")
            rows = await cursor.fetchall()
            return [_format_endpoint(r) for r in rows]
        finally:
            await conn.close()

    async def update_endpoint_status(self, endpoint_id: str, status: str) -> None:
        conn = await get_db_connection(self.db_path)
        try:
            await conn.execute(
                "UPDATE endpoints SET status = ?, updated_at = ? WHERE endpoint_id = ?",
                (status, _now(), endpoint_id),
            )
            await conn.commit()
        finally:
            await conn.close()

    async def update_endpoint_draft(
        self,
        endpoint_id: str,
        target_url: str,
        schema_definition: dict[str, str],
        name: str | None = None,
    ) -> None:
        conn = await get_db_connection(self.db_path)
        try:
            if name:
                await conn.execute(
                    "UPDATE endpoints SET target_url = ?, schema_definition = ?, name = ?, updated_at = ? WHERE endpoint_id = ?",
                    (target_url, json.dumps(schema_definition), name, _now(), endpoint_id),
                )
            else:
                await conn.execute(
                    "UPDATE endpoints SET target_url = ?, schema_definition = ?, updated_at = ? WHERE endpoint_id = ?",
                    (target_url, json.dumps(schema_definition), _now(), endpoint_id),
                )
            await conn.commit()
        finally:
            await conn.close()

    async def atomic_activate_version(
        self, endpoint_id: str, version_id: str
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """
        Atomically promotes a VERIFIED version to ACTIVE in a single transaction.
        Updates previous active version to RETIRED with is_last_known_good=1.
        Raises CandidateNotVerifiedError if candidate is not in VERIFIED status.
        """
        conn = await get_db_connection(self.db_path)
        try:
            await conn.execute("BEGIN TRANSACTION;")

            # 1. Fetch target version
            cursor = await conn.execute(
                "SELECT * FROM endpoint_versions WHERE version_id = ? AND endpoint_id = ?",
                (version_id, endpoint_id),
            )
            target_row = await cursor.fetchone()
            if not target_row:
                await conn.rollback()
                raise MorphApiError(FailureCode.INVALID_CANDIDATE, f"Version '{version_id}' not found for endpoint '{endpoint_id}'")

            target_version = _format_version(target_row)
            if target_version["status"] != "VERIFIED":
                await conn.rollback()
                raise CandidateNotVerifiedError(
                    f"Cannot activate version '{version_id}'. Current status is '{target_version['status']}', expected 'VERIFIED'."
                )

            # 2. Fetch current endpoint to find prior active version
            ep_cursor = await conn.execute(
                "SELECT * FROM endpoints WHERE endpoint_id = ?", (endpoint_id,)
            )
            ep_row = await ep_cursor.fetchone()
            if not ep_row:
                await conn.rollback()
                raise MorphApiError(FailureCode.ENDPOINT_NOT_FOUND, f"Endpoint '{endpoint_id}' not found")

            prior_active_id = ep_row["active_version_id"]
            now = _now()

            # 3. Retire prior active version if exists
            if prior_active_id and prior_active_id != version_id:
                await conn.execute(
                    """
                    UPDATE endpoint_versions
                    SET is_active = 0,
                        status = 'RETIRED',
                        is_last_known_good = 1
                    WHERE version_id = ?
                    """,
                    (prior_active_id,),
                )

            # 4. Activate new version
            await conn.execute(
                """
                UPDATE endpoint_versions
                SET is_active = 1,
                    status = 'ACTIVE',
                    activated_at = ?
                WHERE version_id = ?
                """,
                (now, version_id),
            )

            # 5. Update endpoint record
            last_known_good = prior_active_id or ep_row["last_known_good_version_id"]
            await conn.execute(
                """
                UPDATE endpoints
                SET active_version_id = ?,
                    last_known_good_version_id = ?,
                    status = 'ACTIVE',
                    updated_at = ?
                WHERE endpoint_id = ?
                """,
                (version_id, last_known_good, now, endpoint_id),
            )

            await conn.commit()

            # Fetch fresh records
            refreshed_ep = await (await conn.execute("SELECT * FROM endpoints WHERE endpoint_id = ?", (endpoint_id,))).fetchone()
            refreshed_ver = await (await conn.execute("SELECT * FROM endpoint_versions WHERE version_id = ?", (version_id,))).fetchone()
            return _format_endpoint(refreshed_ep), _format_version(refreshed_ver)
        except Exception:
            await conn.rollback()
            raise
        finally:
            await conn.close()

    async def rollback_to_last_known_good(self, endpoint_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
        """
        Atomically rolls back the active configuration to last_known_good_version_id.
        """
        conn = await get_db_connection(self.db_path)
        try:
            await conn.execute("BEGIN TRANSACTION;")
            cursor = await conn.execute("SELECT * FROM endpoints WHERE endpoint_id = ?", (endpoint_id,))
            ep_row = await cursor.fetchone()
            if not ep_row:
                await conn.rollback()
                raise MorphApiError(FailureCode.ENDPOINT_NOT_FOUND, f"Endpoint '{endpoint_id}' not found")

            lkg_id = ep_row["last_known_good_version_id"]
            if not lkg_id:
                await conn.rollback()
                raise MorphApiError(FailureCode.INVALID_CANDIDATE, f"No last known good version exists for rollback on '{endpoint_id}'")

            current_active_id = ep_row["active_version_id"]
            now = _now()

            # Retire current active
            if current_active_id:
                await conn.execute(
                    "UPDATE endpoint_versions SET is_active = 0, status = 'RETIRED' WHERE version_id = ?",
                    (current_active_id,),
                )

            # Restore last known good version to active
            await conn.execute(
                "UPDATE endpoint_versions SET is_active = 1, status = 'ACTIVE', activated_at = ? WHERE version_id = ?",
                (now, lkg_id),
            )

            # Update endpoint
            await conn.execute(
                """
                UPDATE endpoints
                SET active_version_id = ?,
                    status = 'ACTIVE',
                    updated_at = ?
                WHERE endpoint_id = ?
                """,
                (lkg_id, now, endpoint_id),
            )

            await conn.commit()
            refreshed_ep = await (await conn.execute("SELECT * FROM endpoints WHERE endpoint_id = ?", (endpoint_id,))).fetchone()
            refreshed_ver = await (await conn.execute("SELECT * FROM endpoint_versions WHERE version_id = ?", (lkg_id,))).fetchone()
            return _format_endpoint(refreshed_ep), _format_version(refreshed_ver)
        except Exception:
            await conn.rollback()
            raise
        finally:
            await conn.close()


class VersionRepository:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path

    async def create_candidate_version(
        self,
        endpoint_id: str,
        selector_map: dict[str, str],
        rationale: str | None = None,
        evidence_refs: list[str] | None = None,
        created_by: str = "agent",
    ) -> dict[str, Any]:
        """
        Creates a new candidate version for an endpoint. Does NOT activate or verify it.
        """
        conn = await get_db_connection(self.db_path)
        try:
            # Fetch endpoint schema definition
            ep_cursor = await conn.execute("SELECT schema_definition FROM endpoints WHERE endpoint_id = ?", (endpoint_id,))
            ep_row = await ep_cursor.fetchone()
            if not ep_row:
                raise MorphApiError(FailureCode.ENDPOINT_NOT_FOUND, f"Endpoint '{endpoint_id}' not found")
            schema_def = ep_row["schema_definition"]

            # Calculate next version number
            cursor = await conn.execute(
                "SELECT COALESCE(MAX(version_number), 0) + 1 AS next_ver FROM endpoint_versions WHERE endpoint_id = ?",
                (endpoint_id,),
            )
            next_ver = (await cursor.fetchone())["next_ver"]
            version_id = f"ver_{uuid.uuid4().hex[:12]}"
            now = _now()

            await conn.execute(
                """
                INSERT INTO endpoint_versions (
                    version_id, endpoint_id, version_number, schema_definition,
                    selector_map, status, is_active, is_last_known_good,
                    rationale, evidence_refs, created_by, created_at
                ) VALUES (?, ?, ?, ?, ?, 'CANDIDATE', 0, 0, ?, ?, ?, ?)
                """,
                (
                    version_id,
                    endpoint_id,
                    next_ver,
                    schema_def,
                    json.dumps(selector_map),
                    rationale or "Candidate selector proposal",
                    json.dumps(evidence_refs or []),
                    created_by,
                    now,
                ),
            )
            await conn.commit()

            row = await (await conn.execute("SELECT * FROM endpoint_versions WHERE version_id = ?", (version_id,))).fetchone()
            return _format_version(row)
        finally:
            await conn.close()

    async def get_version(self, version_id: str) -> Optional[dict[str, Any]]:
        conn = await get_db_connection(self.db_path)
        try:
            cursor = await conn.execute("SELECT * FROM endpoint_versions WHERE version_id = ?", (version_id,))
            row = await cursor.fetchone()
            return _format_version(row) if row else None
        finally:
            await conn.close()

    async def list_versions(self, endpoint_id: str) -> list[dict[str, Any]]:
        conn = await get_db_connection(self.db_path)
        try:
            cursor = await conn.execute(
                "SELECT * FROM endpoint_versions WHERE endpoint_id = ? ORDER BY version_number DESC",
                (endpoint_id,),
            )
            rows = await cursor.fetchall()
            return [_format_version(r) for r in rows]
        finally:
            await conn.close()

    async def update_verification_result(
        self, version_id: str, verified: bool, verification_result: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Updates the verification status of a candidate version.
        Only marks status as 'VERIFIED' if verified is True.
        """
        conn = await get_db_connection(self.db_path)
        try:
            now = _now()
            new_status = "VERIFIED" if verified else "REJECTED"
            verified_at = now if verified else None

            await conn.execute(
                """
                UPDATE endpoint_versions
                SET status = ?,
                    verification_result = ?,
                    verified_at = ?
                WHERE version_id = ?
                """,
                (new_status, json.dumps(verification_result), verified_at, version_id),
            )
            await conn.commit()

            row = await (await conn.execute("SELECT * FROM endpoint_versions WHERE version_id = ?", (version_id,))).fetchone()
            return _format_version(row)
        finally:
            await conn.close()


class JobRepository:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path

    async def create_job(
        self,
        endpoint_id: str,
        job_type: str,
        tenant_id: str = "default_tenant",
        workflow_thread_id: str | None = None,
        max_attempts: int = 3,
        deadline: str | None = None,
    ) -> dict[str, Any]:
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        now = _now()
        conn = await get_db_connection(self.db_path)
        try:
            await conn.execute(
                """
                INSERT INTO jobs (
                    job_id, endpoint_id, tenant_id, job_type, workflow_thread_id,
                    status, attempt_count, max_attempts, deadline, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 'PENDING', 0, ?, ?, ?, ?)
                """,
                (job_id, endpoint_id, tenant_id, job_type, workflow_thread_id, max_attempts, deadline, now, now),
            )
            await conn.commit()
            row = await (await conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))).fetchone()
            return _format_job(row)
        finally:
            await conn.close()

    async def get_job(self, job_id: str) -> Optional[dict[str, Any]]:
        conn = await get_db_connection(self.db_path)
        try:
            cursor = await conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
            row = await cursor.fetchone()
            return _format_job(row) if row else None
        finally:
            await conn.close()

    async def update_job_status(
        self,
        job_id: str,
        status: str,
        attempt_count: int | None = None,
        failure_reason: str | None = None,
        result_summary: dict[str, Any] | None = None,
        clarification: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        conn = await get_db_connection(self.db_path)
        try:
            now = _now()
            updates = ["status = ?", "updated_at = ?"]
            params = [status, now]

            if attempt_count is not None:
                updates.append("attempt_count = ?")
                params.append(attempt_count)
            if failure_reason is not None:
                updates.append("failure_reason = ?")
                params.append(failure_reason)
            if result_summary is not None:
                updates.append("result_summary = ?")
                params.append(json.dumps(result_summary))
            if clarification is not None:
                updates.append("clarification = ?")
                params.append(json.dumps(clarification))

            params.append(job_id)
            query = f"UPDATE jobs SET {', '.join(updates)} WHERE job_id = ?"
            await conn.execute(query, tuple(params))
            await conn.commit()

            row = await (await conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))).fetchone()
            return _format_job(row)
        finally:
            await conn.close()

    async def list_jobs(self, endpoint_id: str) -> list[dict[str, Any]]:
        conn = await get_db_connection(self.db_path)
        try:
            cursor = await conn.execute(
                "SELECT * FROM jobs WHERE endpoint_id = ? ORDER BY created_at DESC", (endpoint_id,)
            )
            rows = await cursor.fetchall()
            return [_format_job(r) for r in rows]
        finally:
            await conn.close()


class AuditRepository:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path

    async def append_event(
        self,
        correlation_id: str,
        action: str,
        target_type: str,
        target_id: str,
        tenant_id: str = "default_tenant",
        actor: str = "system",
        details: dict[str, Any] | None = None,
    ) -> int:
        now = _now()
        conn = await get_db_connection(self.db_path)
        try:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    correlation_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL DEFAULT 'default_tenant',
                    actor TEXT NOT NULL DEFAULT 'system',
                    action TEXT NOT NULL,
                    target_type TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    details TEXT NOT NULL DEFAULT '{}',
                    timestamp TEXT NOT NULL
                );
                """
            )
            cursor = await conn.execute(
                """
                INSERT INTO audit_events (
                    correlation_id, tenant_id, actor, action, target_type, target_id, details, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (correlation_id, tenant_id, actor, action, target_type, target_id, json.dumps(details or {}), now),
            )
            await conn.commit()
            return cursor.lastrowid
        finally:
            await conn.close()

    async def list_events_for_target(self, target_id: str, limit: int = 50) -> list[dict[str, Any]]:
        conn = await get_db_connection(self.db_path)
        try:
            cursor = await conn.execute(
                """
                SELECT * FROM audit_events 
                WHERE target_id = ? 
                   OR target_id IN (SELECT version_id FROM endpoint_versions WHERE endpoint_id = ?)
                ORDER BY audit_id DESC LIMIT ?
                """,
                (target_id, target_id, limit),
            )
            rows = await cursor.fetchall()
            return [_format_audit(r) for r in rows]
        finally:
            await conn.close()
