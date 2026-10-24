"""
Unit Tests for MorphAPI V2 Observability & Structured Logging
"""

import json
import logging
import pytest
from httpx import AsyncClient, ASGITransport
from morphapi_v2.observability.correlation import get_correlation_id, set_correlation_id
from morphapi_v2.observability.logging import redact_secrets, RedactingFormatterV2, JsonFormatterV2
from morphapi_v2.api.app import app


def test_secret_redaction():
    # Test NIM API key redaction
    sample_1 = "Using key nvapi-abc123def456ghi789jkl012 to call endpoint"
    redacted_1 = redact_secrets(sample_1)
    assert "nvapi-" not in redacted_1
    assert "[REDACTED_SECRET]" in redacted_1

    # Test MorphAPI client key redaction
    sample_2 = "Generated key mapik_yc-startups-_0ea6a46c164228da061e7034 for client"
    redacted_2 = redact_secrets(sample_2)
    assert "mapik_" not in redacted_2
    assert "[REDACTED_SECRET]" in redacted_2

    # Test Bearer token redaction
    sample_3 = "Authorization: Bearer mySecretToken123456789"
    redacted_3 = redact_secrets(sample_3)
    assert "mySecretToken" not in redacted_3

    # Test password redaction
    sample_4 = "Connecting with password=SuperSecretPassword123"
    redacted_4 = redact_secrets(sample_4)
    assert "SuperSecretPassword123" not in redacted_4


def test_redacting_formatter():
    set_correlation_id("test_cid_999")
    formatter = RedactingFormatterV2(fmt="%(asctime)s [cid=%(correlation_id)s] %(message)s")
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="Calling provider with nvapi-12345678901234567890",
        args=(),
        exc_info=None,
    )
    formatted = formatter.format(record)
    assert "test_cid_999" in formatted
    assert "nvapi-" not in formatted
    assert "[REDACTED_SECRET]" in formatted


def test_json_formatter():
    set_correlation_id("test_json_cid")
    formatter = JsonFormatterV2()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.WARNING,
        pathname=__file__,
        lineno=42,
        msg="Warning with secret password=pass123456",
        args=(),
        exc_info=None,
    )
    formatted = formatter.format(record)
    parsed = json.loads(formatted)
    assert parsed["level"] == "WARNING"
    assert parsed["correlation_id"] == "test_json_cid"
    assert "pass123456" not in parsed["message"]


@pytest.mark.asyncio
async def test_correlation_id_middleware_and_access_logging():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Send request with custom correlation ID
        resp = await client.get("/v2/health", headers={"X-Correlation-ID": "custom_cid_123"})
        assert resp.status_code == 200
        # Response must return the same correlation ID
        assert resp.headers.get("X-Correlation-ID") == "custom_cid_123"

        # Send request without header -> must auto-generate one
        resp_auto = await client.get("/v2/health")
        assert resp_auto.status_code == 200
        auto_cid = resp_auto.headers.get("X-Correlation-ID")
        assert auto_cid is not None
        assert auto_cid.startswith("v2_req_")
