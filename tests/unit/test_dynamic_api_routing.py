"""
Tests for MorphAPI Dynamic API Routing & Runtime Parameterization.
Verifies /v1/api/{user_id}/{api_name} paths and dynamic query/template forwarding.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from morphapi.services.extraction_service import SharedExtractionService
from morphapi.schemas.contracts import ExtractionResult, ValidationResult


@pytest.mark.asyncio
async def test_dynamic_url_template_substitution():
    """Verify that {param} template placeholders are substituted with runtime query params."""
    mock_extractor = AsyncMock()
    mock_extractor.extract = AsyncMock(return_value=ExtractionResult(
        success=True,
        data=[{"name": "Acme Corp"}],
        field_evidences=[],
        page_title="YC",
        target_url="https://www.ycombinator.com/companies?batch=W25",
        latency_ms=10,
    ))

    mock_validator = MagicMock()
    mock_validator.validate_extraction.return_value = ValidationResult(
        is_valid=True,
        normalized_data=[{"name": "Acme Corp"}],
        errors=[],
    )

    mock_endpoint_repo = AsyncMock()
    mock_endpoint_repo.get_endpoint.return_value = {
        "endpoint_id": "ep_yc123",
        "slug": "yc-startups",
        "target_url": "https://www.ycombinator.com/companies?batch={batch}",
        "active_version_id": "ver_yc123",
        "status": "ACTIVE",
    }

    mock_version_repo = AsyncMock()
    mock_version_repo.get_version.return_value = {
        "version_number": 1,
        "is_active": True,
        "schema_definition": {"name": "str"},
        "selector_map": {"name": "a.company"},
    }

    svc = SharedExtractionService(
        extractor=mock_extractor,
        validator=mock_validator,
        endpoint_repo=mock_endpoint_repo,
        version_repo=mock_version_repo,
    )

    # Call with runtime param batch=W25
    resp = await svc.extract_endpoint("yc-startups", tenant_id="alice", params={"batch": "W25"})
    assert resp.data == [{"name": "Acme Corp"}]

    # Assert that extractor was called with the dynamically substituted URL
    call_args = mock_extractor.extract.call_args
    assert call_args is not None
    assert call_args.kwargs["target_url"] == "https://www.ycombinator.com/companies?batch=W25"


@pytest.mark.asyncio
async def test_dynamic_query_param_appending():
    """Verify that runtime query params are forwarded to target URLs without templates."""
    mock_extractor = AsyncMock()
    mock_extractor.extract = AsyncMock(return_value=ExtractionResult(
        success=True,
        data=[{"company": "Beta AI"}],
        field_evidences=[],
        page_title="Startups",
        target_url="https://example.com/companies?year=2026",
        latency_ms=10,
    ))

    mock_validator = MagicMock()
    mock_validator.validate_extraction.return_value = ValidationResult(
        is_valid=True,
        normalized_data=[{"company": "Beta AI"}],
        errors=[],
    )

    mock_endpoint_repo = AsyncMock()
    mock_endpoint_repo.get_endpoint.return_value = {
        "endpoint_id": "ep_123",
        "slug": "startups",
        "target_url": "https://example.com/companies",
        "active_version_id": "ver_123",
        "status": "ACTIVE",
    }

    mock_version_repo = AsyncMock()
    mock_version_repo.get_version.return_value = {
        "version_number": 1,
        "is_active": True,
        "schema_definition": {"company": "str"},
        "selector_map": {"company": ".name"},
    }

    svc = SharedExtractionService(
        extractor=mock_extractor,
        validator=mock_validator,
        endpoint_repo=mock_endpoint_repo,
        version_repo=mock_version_repo,
    )

    resp = await svc.extract_endpoint("startups", tenant_id="bob", params={"year": "2026"})
    assert resp.data == [{"company": "Beta AI"}]

    call_args = mock_extractor.extract.call_args
    assert "year=2026" in call_args.kwargs["target_url"]
