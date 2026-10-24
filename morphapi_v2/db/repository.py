"""
Isolated Database Repository for MorphAPI V2
"""

import json
import logging
import sqlite3
from typing import Any
import aiosqlite

from morphapi_v2.config import settings

logger = logging.getLogger("morphapi_v2.db")


class EndpointRepositoryV2:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or settings.db_path

    async def init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS v2_endpoints (
                    endpoint_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    api_name TEXT NOT NULL,
                    slug TEXT NOT NULL,
                    target_url TEXT NOT NULL,
                    schema_definition TEXT NOT NULL,
                    inputs TEXT NOT NULL,
                    plan TEXT NOT NULL,
                    sample_data TEXT NOT NULL,
                    api_key TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, slug)
                );
            """)
            await db.commit()

    async def save_endpoint(
        self,
        endpoint_id: str,
        user_id: str,
        api_name: str,
        slug: str,
        target_url: str,
        schema_definition: dict[str, Any],
        inputs: dict[str, Any],
        plan: dict[str, Any],
        sample_data: list[dict[str, Any]],
        api_key: str,
    ):
        await self.init_db()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO v2_endpoints (
                    endpoint_id, user_id, api_name, slug, target_url,
                    schema_definition, inputs, plan, sample_data, api_key, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP);
            """, (
                endpoint_id,
                user_id,
                api_name,
                slug,
                target_url,
                json.dumps(schema_definition),
                json.dumps(inputs),
                json.dumps(plan),
                json.dumps(sample_data),
                api_key,
            ))
            await db.commit()

    async def get_endpoint(self, user_id: str, slug: str) -> dict[str, Any] | None:
        await self.init_db()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM v2_endpoints WHERE user_id = ? AND slug = ?;
            """, (user_id, slug))
            row = await cursor.fetchone()
            if not row:
                return None
            return {
                "endpoint_id": row["endpoint_id"],
                "user_id": row["user_id"],
                "api_name": row["api_name"],
                "slug": row["slug"],
                "target_url": row["target_url"],
                "schema_definition": json.loads(row["schema_definition"]),
                "inputs": json.loads(row["inputs"]),
                "plan": json.loads(row["plan"]),
                "sample_data": json.loads(row["sample_data"]),
                "api_key": row["api_key"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }

    async def list_endpoints(self, user_id: str | None = None) -> list[dict[str, Any]]:
        await self.init_db()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if user_id:
                cursor = await db.execute("SELECT * FROM v2_endpoints WHERE user_id = ? ORDER BY created_at DESC;", (user_id,))
            else:
                cursor = await db.execute("SELECT * FROM v2_endpoints ORDER BY created_at DESC;")
            rows = await cursor.fetchall()
            return [
                {
                    "endpoint_id": r["endpoint_id"],
                    "user_id": r["user_id"],
                    "api_name": r["api_name"],
                    "slug": r["slug"],
                    "target_url": r["target_url"],
                    "schema_definition": json.loads(r["schema_definition"]),
                    "inputs": json.loads(r["inputs"]),
                    "sample_data": json.loads(r["sample_data"]),
                    "api_key": r["api_key"],
                }
                for r in rows
            ]


endpoint_repo_v2 = EndpointRepositoryV2()
