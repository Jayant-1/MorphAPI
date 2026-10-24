"""
MorphAPI V2 Correlation ID & Context Tracking
"""

import uuid
from contextvars import ContextVar
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_v2_correlation_id_ctx: ContextVar[str] = ContextVar("v2_correlation_id", default="")


def get_correlation_id() -> str:
    """Returns active correlation ID or generates a new one."""
    cid = _v2_correlation_id_ctx.get()
    if not cid:
        cid = f"v2_req_{uuid.uuid4().hex[:12]}"
        _v2_correlation_id_ctx.set(cid)
    return cid


def set_correlation_id(cid: str) -> None:
    _v2_correlation_id_ctx.set(cid)


class CorrelationIdMiddlewareV2(BaseHTTPMiddleware):
    """Captures or generates X-Correlation-ID for each request."""

    async def dispatch(self, request: Request, call_next) -> Response:
        cid = (
            request.headers.get("X-Correlation-ID")
            or request.headers.get("X-Request-ID")
            or f"v2_req_{uuid.uuid4().hex[:12]}"
        )
        token = _v2_correlation_id_ctx.set(cid)
        request.state.correlation_id = cid
        try:
            response = await call_next(request)
            response.headers["X-Correlation-ID"] = cid
            return response
        finally:
            _v2_correlation_id_ctx.reset(token)
