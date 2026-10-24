"""
MorphAPI Database Layer (SQLite via aiosqlite)
Canonical SQLite schema implementation for endpoints, healing logs, and telemetry.
"""

import json
import os
import aiosqlite
from datetime import datetime, timezone
from typing import Any, Optional

DB_PATH = os.getenv("DB_PATH", "./morphapi.db")


async def get_db_connection() -> aiosqlite.Connection:
    conn = await aiosqlite.connect(DB_PATH)
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA foreign_keys = ON;")
    return conn


async def init_db():
    async with await get_db_connection() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS endpoints (
                endpoint_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                target_url TEXT NOT NULL,
                schema_definition TEXT NOT NULL,
                initial_selectors TEXT,
                status TEXT NOT NULL DEFAULT 'HEALTHY',
                version INTEGER NOT NULL DEFAULT 1,
                last_verified TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS healing_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                endpoint_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                failure_reason TEXT NOT NULL,
                old_selectors TEXT NOT NULL,
                new_selectors TEXT NOT NULL,
                ai_reasoning TEXT NOT NULL,
                screenshot_b64 TEXT,
                heal_latency_ms INTEGER NOT NULL,
                from_version INTEGER NOT NULL,
                to_version INTEGER NOT NULL,
                FOREIGN KEY (endpoint_id) REFERENCES endpoints(endpoint_id) ON DELETE CASCADE
            );
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS request_telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                endpoint_id TEXT NOT NULL,
                execution_path TEXT NOT NULL,
                latency_ms INTEGER NOT NULL,
                tokens_used INTEGER,
                http_status INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (endpoint_id) REFERENCES endpoints(endpoint_id) ON DELETE CASCADE
            );
        """)
        await conn.commit()


# Repository operations
async def register_endpoint(
    endpoint_id: str,
    name: str,
    target_url: str,
    schema_definition: dict[str, str],
    initial_selectors: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    async with await get_db_connection() as conn:
        await conn.execute(
            """
            INSERT INTO endpoints (
                endpoint_id, name, target_url, schema_definition, initial_selectors,
                status, version, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 'HEALTHY', 1, ?, ?)
            ON CONFLICT(endpoint_id) DO UPDATE SET
                name=excluded.name,
                target_url=excluded.target_url,
                schema_definition=excluded.schema_definition,
                initial_selectors=excluded.initial_selectors,
                updated_at=excluded.updated_at
            """,
            (
                endpoint_id,
                name,
                target_url,
                json.dumps(schema_definition),
                json.dumps(initial_selectors) if initial_selectors else None,
                now,
                now,
            ),
        )
        await conn.commit()

        cursor = await conn.execute(
            "SELECT * FROM endpoints WHERE endpoint_id = ?", (endpoint_id,)
        )
        row = await cursor.fetchone()
        return _format_endpoint(row)


async def get_endpoint(endpoint_id: str) -> Optional[dict[str, Any]]:
    async with await get_db_connection() as conn:
        cursor = await conn.execute(
            "SELECT * FROM endpoints WHERE endpoint_id = ?", (endpoint_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return _format_endpoint(row)


async def list_endpoints() -> list[dict[str, Any]]:
    async with await get_db_connection() as conn:
        cursor = await conn.execute(
            "SELECT * FROM endpoints ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()
        return [_format_endpoint(r) for r in rows]


async def update_endpoint_selectors(
    endpoint_id: str,
    new_selectors: dict[str, str],
    new_version: int,
    status: str = "HEALTHY",
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    async with await get_db_connection() as conn:
        await conn.execute(
            """
            UPDATE endpoints
            SET initial_selectors = ?,
                version = ?,
                status = ?,
                last_verified = ?,
                updated_at = ?
            WHERE endpoint_id = ?
            """,
            (
                json.dumps(new_selectors),
                new_version,
                status,
                now,
                now,
                endpoint_id,
            ),
        )
        await conn.commit()


async def update_endpoint_status(endpoint_id: str, status: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    async with await get_db_connection() as conn:
        await conn.execute(
            "UPDATE endpoints SET status = ?, updated_at = ? WHERE endpoint_id = ?",
            (status, now, endpoint_id),
        )
        await conn.commit()


async def record_healing_log(
    endpoint_id: str,
    failure_reason: str,
    old_selectors: dict[str, str],
    new_selectors: dict[str, str],
    ai_reasoning: str,
    screenshot_b64: Optional[str],
    heal_latency_ms: int,
    from_version: int,
    to_version: int,
) -> int:
    now = datetime.now(timezone.utc).isoformat()
    async with await get_db_connection() as conn:
        cursor = await conn.execute(
            """
            INSERT INTO healing_logs (
                endpoint_id, timestamp, failure_reason, old_selectors,
                new_selectors, ai_reasoning, screenshot_b64, heal_latency_ms,
                from_version, to_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                endpoint_id,
                now,
                failure_reason,
                json.dumps(old_selectors),
                json.dumps(new_selectors),
                ai_reasoning,
                screenshot_b64,
                heal_latency_ms,
                from_version,
                to_version,
            ),
        )
        # Enforce max 50 healing logs per endpoint per SRS requirement
        await conn.execute(
            """
            DELETE FROM healing_logs
            WHERE endpoint_id = ? AND log_id NOT IN (
                SELECT log_id FROM healing_logs
                WHERE endpoint_id = ?
                ORDER BY log_id DESC
                LIMIT 50
            )
            """,
            (endpoint_id, endpoint_id),
        )
        await conn.commit()
        return cursor.lastrowid


async def get_healing_logs(endpoint_id: str, limit: int = 50) -> list[dict[str, Any]]:
    async with await get_db_connection() as conn:
        cursor = await conn.execute(
            """
            SELECT * FROM healing_logs
            WHERE endpoint_id = ?
            ORDER BY log_id DESC
            LIMIT ?
            """,
            (endpoint_id, limit),
        )
        rows = await cursor.fetchall()
        result = []
        for r in rows:
            result.append({
                "log_id": r["log_id"],
                "endpoint_id": r["endpoint_id"],
                "timestamp": r["timestamp"],
                "failure_reason": r["failure_reason"],
                "old_selectors": json.loads(r["old_selectors"]) if r["old_selectors"] else {},
                "new_selectors": json.loads(r["new_selectors"]) if r["new_selectors"] else {},
                "ai_reasoning": r["ai_reasoning"],
                "screenshot_b64": r["screenshot_b64"],
                "heal_latency_ms": r["heal_latency_ms"],
                "from_version": r["from_version"],
                "to_version": r["to_version"],
            })
        return result


async def record_telemetry(
    endpoint_id: str,
    execution_path: str,
    latency_ms: int,
    http_status: int = 200,
    tokens_used: Optional[int] = None,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    async with await get_db_connection() as conn:
        await conn.execute(
            """
            INSERT INTO request_telemetry (
                endpoint_id, execution_path, latency_ms, tokens_used, http_status, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (endpoint_id, execution_path, latency_ms, tokens_used, http_status, now),
        )
        await conn.commit()


async def get_telemetry_summary() -> dict[str, Any]:
    async with await get_db_connection() as conn:
        cursor = await conn.execute("SELECT COUNT(*) as total FROM request_telemetry")
        total = (await cursor.fetchone())["total"]

        cursor = await conn.execute(
            "SELECT COUNT(*) as fast FROM request_telemetry WHERE execution_path = 'FAST_PATH'"
        )
        fast_count = (await cursor.fetchone())["fast"]

        cursor = await conn.execute(
            "SELECT COUNT(*) as healed FROM request_telemetry WHERE execution_path = 'SELF_HEALED'"
        )
        healed_count = (await cursor.fetchone())["healed"]

        cursor = await conn.execute("SELECT AVG(latency_ms) as avg_lat FROM request_telemetry")
        avg_lat = (await cursor.fetchone())["avg_lat"] or 0.0

        cursor = await conn.execute("SELECT COUNT(*) as active FROM endpoints WHERE status = 'HEALTHY'")
        active_ep = (await cursor.fetchone())["active"]

        cursor = await conn.execute("SELECT COUNT(*) as degraded FROM endpoints WHERE status = 'DEGRADED'")
        degraded_ep = (await cursor.fetchone())["degraded"]

        cursor = await conn.execute(
            """
            SELECT * FROM request_telemetry
            ORDER BY id DESC
            LIMIT 20
            """
        )
        recent_rows = await cursor.fetchall()
        recent_telemetry = [
            {
                "id": r["id"],
                "endpoint_id": r["endpoint_id"],
                "execution_path": r["execution_path"],
                "latency_ms": r["latency_ms"],
                "http_status": r["http_status"],
                "timestamp": r["timestamp"],
            }
            for r in recent_rows
        ]

        hit_rate = round((fast_count / total * 100), 1) if total > 0 else 100.0

        return {
            "total_requests": total,
            "fast_path_count": fast_count,
            "self_healed_count": healed_count,
            "fast_path_hit_rate": hit_rate,
            "avg_latency_ms": round(float(avg_lat), 1),
            "active_endpoints": active_ep,
            "degraded_endpoints": degraded_ep,
            "recent_telemetry": recent_telemetry,
        }


def _format_endpoint(row: aiosqlite.Row) -> dict[str, Any]:
    return {
        "endpoint_id": row["endpoint_id"],
        "name": row["name"],
        "target_url": row["target_url"],
        "schema_definition": json.loads(row["schema_definition"]) if row["schema_definition"] else {},
        "initial_selectors": json.loads(row["initial_selectors"]) if row["initial_selectors"] else {},
        "status": row["status"],
        "version": row["version"],
        "last_verified": row["last_verified"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
