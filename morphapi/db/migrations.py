"""
MorphAPI Database Migration Runner
Bootstraps tables and default records idempotently.
"""

from datetime import datetime, timezone
import aiosqlite
from morphapi.config import settings
from morphapi.db.connection import get_db_connection
from morphapi.db.models import SCHEMA_DDL
from morphapi.observability.logging import logger


async def run_migrations(db_path: str | None = None) -> None:
    """
    Executes all schema creation statements and initializes the default tenant.
    """
    conn = await get_db_connection(db_path)
    try:
        logger.info(f"Running database migrations on {db_path or settings.db_path}...")
        await conn.executescript(SCHEMA_DDL)

        # Seed default tenant if not existing
        now = datetime.now(timezone.utc).isoformat()
        await conn.execute(
            """
            INSERT OR IGNORE INTO tenants (tenant_id, name, policy_settings, created_at)
            VALUES (?, ?, '{}', ?)
            """,
            (settings.default_tenant_id, "Default Organization", now),
        )
        await conn.commit()
        logger.info("Database schema initialized successfully.")
    finally:
        await conn.close()
