"""
MorphAPI FastAPI Gateway Application
Control plane, REST routes, lifespan, middleware, and stable error translation.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from morphapi.api import (
    audit_router,
    endpoints_router,
    extract_router,
    health_router,
    jobs_router,
)
from morphapi.config import settings
from morphapi.db.migrations import run_migrations
from morphapi.observability import CorrelationIdMiddleware, get_correlation_id, logger, redact_secrets
from morphapi.schemas.errors import FailureCode, MorphApiError


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing MorphAPI SQLite database and running migrations...")
    await run_migrations()
    logger.info("MorphAPI Gateway initialized and ready.")
    yield
    logger.info("Shutting down MorphAPI Gateway...")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description="Self-healing Web-to-API and MCP Gateway",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Middleware
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global Exception Handlers for Stable Error Responses
    @app.exception_handler(MorphApiError)
    async def morph_api_error_handler(request: Request, exc: MorphApiError):
        cid = getattr(request.state, "correlation_id", None) or get_correlation_id()
        status_code = status.HTTP_400_BAD_REQUEST
        if exc.code == FailureCode.ENDPOINT_NOT_FOUND:
            status_code = status.HTTP_404_NOT_FOUND
        elif exc.code in (FailureCode.INVALID_CANDIDATE, FailureCode.SCHEMA_VALIDATION_FAILED):
            status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        elif exc.code == FailureCode.BROWSER_TIMEOUT:
            status_code = status.HTTP_504_GATEWAY_TIMEOUT
        elif exc.code in (FailureCode.SSRF_DETECTED, FailureCode.DISALLOWED_URL):
            status_code = status.HTTP_403_FORBIDDEN
        elif exc.code in (FailureCode.WORKFLOW_FAILED, FailureCode.SELECTOR_NOT_FOUND, FailureCode.BROWSER_RESOURCE_ERROR):
            status_code = status.HTTP_502_BAD_GATEWAY

        safe_message = redact_secrets(exc.message)
        logger.warning(f"Domain error [{exc.code.value}]: {safe_message}")
        return JSONResponse(
            status_code=status_code,
            content={
                "error_code": exc.code.value if hasattr(exc.code, "value") else str(exc.code),
                "message": safe_message,
                "correlation_id": cid,
                "retryable": exc.retryable,
                "details": exc.details,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        cid = getattr(request.state, "correlation_id", None) or get_correlation_id()
        logger.warning(f"Request validation error: {exc.errors()}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error_code": FailureCode.SCHEMA_VALIDATION_FAILED.value,
                "message": "Request payload validation failed.",
                "correlation_id": cid,
                "details": {"validation_errors": exc.errors()},
            },
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        cid = getattr(request.state, "correlation_id", None) or get_correlation_id()
        logger.exception(f"Unhandled server error: {exc}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error_code": "INTERNAL_SERVER_ERROR",
                "message": redact_secrets(str(exc)),
                "correlation_id": cid,
            },
        )

    # Mount API routers
    app.include_router(health_router)
    app.include_router(endpoints_router)
    app.include_router(extract_router)
    app.include_router(jobs_router)
    app.include_router(audit_router)

    return app


app = create_app()
