"""
MorphAPI Database Connection Layer
Asynchronous SQLite connection management via aiosqlite.
"""

import aiosqlite
from morphapi.config import settings


async def get_db_connection(db_path: str | None = None) -> aiosqlite.Connection:
    """
    Returns an aiosqlite connection configured with Row factory and foreign keys enabled.
    """
    path = db_path or settings.db_path
    conn = await aiosqlite.connect(path)
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA foreign_keys = ON;")
    await conn.execute("PRAGMA journal_mode = WAL;")
    return conn
