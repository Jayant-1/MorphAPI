"""
Unit Tests for Observability, Structured Logging & Secret Redaction
Tests correlation ID context, header propagation, and credential redaction.
"""

import pytest
from morphapi.observability.correlation import (
    get_correlation_id,
    set_correlation_id,
)
from morphapi.observability.logging import redact_secrets


def test_correlation_id_generation_and_override():
    cid = get_correlation_id()
    assert cid is not None
    assert len(cid) > 8

    custom_cid = "custom-trace-uuid-1234"
    set_correlation_id(custom_cid)
    assert get_correlation_id() == custom_cid


def test_redact_secrets():
    # NIM api key format
    raw_nim = "Error connecting to model with key nvapi-abc1234567890abcdefghijklmn"
    redacted_nim = redact_secrets(raw_nim)
    assert "[REDACTED_SECRET]" in redacted_nim
    assert "abc1234567890abcdefghijklmn" not in redacted_nim

    # Bearer token
    raw_bearer = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIi"
    redacted_bearer = redact_secrets(raw_bearer)
    assert "[REDACTED_SECRET]" in redacted_bearer
    assert "eyJhbGci" not in redacted_bearer

    # Passwords in URLs
    raw_url = "Connecting to http://admin:supersecretpassword@10.0.0.1:5432/db"
    redacted_url = redact_secrets(raw_url)
    assert "supersecretpassword" not in redacted_url
    assert "[REDACTED_SECRET]" in redacted_url
