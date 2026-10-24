"""
MorphAPI Gateway Main Application
FastAPI REST & WebSocket gateway implementing docs/SHARED_CONTRACT.md
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.database import init_db
from backend.app.routes import endpoints, extract, telemetry
from backend.app.services.orchestrator import orchestrator_instance

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("morphapi.gateway")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing MorphAPI SQLite database...")
    await init_db()
    logger.info("MorphAPI Gateway initialized and ready.")
    yield
    logger.info("Shutting down MorphAPI Gateway and Playwright browser pool...")
    try:
        await orchestrator_instance.extractor.close()
    except Exception as e:
        logger.warning(f"Error closing Playwright browser: {e}")


app = FastAPI(
    title="MorphAPI Gateway",
    description="The Self-Healing Multimodal Web-to-API & MCP Gateway",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(endpoints.router)
app.include_router(extract.router)
app.include_router(telemetry.router)


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "ok",
        "service": "MorphAPI Gateway",
        "version": "1.0.0",
    }
