"""
MorphAPI V2 Structured Logging & Secret Redaction
Provides structured log entries with automatic secret redaction,
correlation ID injection, and HTTP request/response metrics.
"""

import json
import logging
import re
import time
from typing import Any
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from morphapi_v2.config import settings
from morphapi_v2.observability.correlation import get_correlation_id

REDACTION_PATTERNS = [
    re.compile(r"nvapi-[A-Za-z0-9_-]{20,}", re.IGNORECASE),
    re.compile(r"mapik_[A-Za-z0-9_-]{20,}", re.IGNORECASE),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}", re.IGNORECASE),
    re.compile(r"(?:bearer\s+|api[_-]?key[\s:=]+)([A-Za-z0-9_\-\.]{16,})", re.IGNORECASE),
    re.compile(r"(?:password|secret|token)[\s:=]+['\"]?([^'\"\s]+)", re.IGNORECASE),
    re.compile(r"(https?://[^:]+:)[^@]+(@)", re.IGNORECASE),
]


def redact_secrets(text: str) -> str:
    """Sanitizes text by replacing known secret patterns and tokens with redaction tags."""
    if not text or not isinstance(text, str):
        return text

    redacted = text
    if settings.nvidia_nim_api_key and len(settings.nvidia_nim_api_key) > 5:
        redacted = redacted.replace(settings.nvidia_nim_api_key, "[REDACTED_NIM_KEY]")

    for pattern in REDACTION_PATTERNS:
        redacted = pattern.sub("[REDACTED_SECRET]", redacted)

    return redacted


class RedactingFormatterV2(logging.Formatter):
    """Console formatter with correlation ID and secret redaction."""

    def format(self, record: logging.LogRecord) -> str:
        record.correlation_id = get_correlation_id()
        msg = super().format(record)
        return redact_secrets(msg)


class JsonFormatterV2(logging.Formatter):
    """Structured JSON formatter for machine-readable observability."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "correlation_id": get_correlation_id(),
            "logger": record.name,
            "message": redact_secrets(record.getMessage()),
            "module": record.module,
            "line": record.lineno,
        }
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)


def setup_logging_v2(level: int = logging.INFO, json_format: bool = False) -> logging.Logger:
    """Initializes and returns configured root logger for morphapi_v2."""
    logger = logging.getLogger("morphapi_v2")
    logger.setLevel(level)
    logger.propagate = False

    # Avoid duplicate handlers
    if not logger.handlers:
        handler = logging.StreamHandler()
        if json_format:
            handler.setFormatter(JsonFormatterV2())
        else:
            handler.setFormatter(
                RedactingFormatterV2(
                    fmt="%(asctime)s [%(levelname)s] [cid=%(correlation_id)s] %(name)s: %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )
        logger.addHandler(handler)

    return logger


logger = setup_logging_v2()


class RequestLoggingMiddlewareV2(BaseHTTPMiddleware):
    """Logs incoming requests, response status, and duration in ms."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start_ts = time.monotonic()
        method = request.method
        url_path = request.url.path
        query = str(request.query_params)
        cid = getattr(request.state, "correlation_id", get_correlation_id())

        logger.info("[HTTP IN] %s %s (params: %s)", method, url_path, query if query else "none")

        try:
            response = await call_next(request)
            duration_ms = int((time.monotonic() - start_ts) * 1000)
            logger.info(
                "[HTTP OUT] %s %s -> Status: %d (%dms)",
                method,
                url_path,
                response.status_code,
                duration_ms,
            )
            return response
        except Exception as e:
            duration_ms = int((time.monotonic() - start_ts) * 1000)
            logger.error(
                "[HTTP ERR] %s %s -> Exception: %s (%dms)",
                method,
                url_path,
                redact_secrets(str(e)),
                duration_ms,
            )
            raise
