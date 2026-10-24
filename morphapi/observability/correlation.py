"""
MorphAPI Correlation ID & Request Tracing
Provides contextual request and workflow correlation tracking.
"""

import uuid
from contextvars import ContextVar
from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Context variable for holding correlation id across async tasks
_correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    """Returns the active correlation ID or generates a new one."""
    cid = _correlation_id_ctx.get()
    if not cid:
        cid = str(uuid.uuid4())
        _correlation_id_ctx.set(cid)
    return cid


def set_correlation_id(cid: str) -> None:
    """Sets the active correlation ID for the current context."""
    _correlation_id_ctx.set(cid)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware that captures or generates X-Correlation-ID for each HTTP request
    and attaches it to the response header.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        cid = request.headers.get("X-Correlation-ID") or request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = _correlation_id_ctx.set(cid)
        request.state.correlation_id = cid
        try:
            response = await call_next(request)
            response.headers["X-Correlation-ID"] = cid
            return response
        finally:
            _correlation_id_ctx.reset(token)
