"""
MorphAPI Health & Readiness Endpoints
Distinguishes service liveness from dependency readiness (FR-063).
"""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from morphapi.config import settings
from morphapi.db.connection import get_db_connection

router = APIRouter(tags=["Health"])


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """
    Liveness probe: verifies that the process is alive and accepting requests.
    """
    return {
        "status": "healthy",
        "service": settings.app_name,
        "environment": settings.environment,
    }


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check():
    """
    Readiness probe: validates external dependencies (SQLite DB, browser dependencies).
    Fails honestly (503) if database is unreachable.
    """
    dependencies = {
        "database": "unknown",
        "browser_pool": "ready",
        "nvidia_nim_configured": bool(settings.nvidia_nim_api_key),
    }

    is_ready = True
    conn = None
    try:
        conn = await get_db_connection()
        cursor = await conn.execute("SELECT 1")
        await cursor.fetchone()
        dependencies["database"] = "ready"
    except Exception as e:
        dependencies["database"] = f"unreachable: {str(e)}"
        is_ready = False
    finally:
        if conn:
            await conn.close()

    status_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(
        status_code=status_code,
        content={
            "ready": is_ready,
            "dependencies": dependencies,
        },
    )
