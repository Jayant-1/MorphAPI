"""
MorphAPI Structured Logging & Secret Redaction
Outputs structured log entries with automatic credential and token redaction.
"""

import logging
import re
from typing import Any
from morphapi.config import settings
from morphapi.observability.correlation import get_correlation_id

# Regexes for redaction
REDACTION_PATTERNS = [
    re.compile(r"nvapi-[A-Za-z0-9_-]{20,}", re.IGNORECASE),
    re.compile(r"(?:bearer\s+|api[_-]?key[\s:=]+)([A-Za-z0-9_\-\.]{16,})", re.IGNORECASE),
    re.compile(r"(?:password|secret)[\s:=]+['\"]?([^'\"\s]+)", re.IGNORECASE),
    re.compile(r"(https?://[^:]+:)[^@]+(@)", re.IGNORECASE),
]


def redact_secrets(text: str) -> str:
    """Redacts known secret patterns and credentials from strings."""
    if not text or not isinstance(text, str):
        return text

    redacted = text
    if settings.nvidia_nim_api_key and len(settings.nvidia_nim_api_key) > 4:
        redacted = redacted.replace(settings.nvidia_nim_api_key, "[REDACTED_API_KEY]")

    for pattern in REDACTION_PATTERNS:
        redacted = pattern.sub("[REDACTED_SECRET]", redacted)

    return redacted


class RedactingFormatter(logging.Formatter):
    """Logging formatter that redacts secrets and appends correlation ID."""

    def format(self, record: logging.LogRecord) -> str:
        record.correlation_id = get_correlation_id()
        original_msg = super().format(record)
        return redact_secrets(original_msg)


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configures root logging with redacting formatter."""
    logger = logging.getLogger("morphapi")
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = RedactingFormatter(
            fmt="%(asctime)s [%(levelname)s] [cid=%(correlation_id)s] %(name)s: %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger


logger = setup_logging()
