"""
Contract Tests for MorphAPI REST API
Tests all routes against FastAPI application using HTTPX AsyncClient.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from morphapi.app import app
from morphapi.config import settings
from morphapi.db.migrations import run_migrations


@pytest_asyncio.fixture(autouse=True)
async def init_test_db(tmp_path, monkeypatch):
    test_db = str(tmp_path / "test_api.db")
    monkeypatch.setattr(settings, "db_path", test_db)
    await run_migrations(db_path=test_db)


@pytest.mark.asyncio
async def test_health_and_readiness_endpoints():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Liveness
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

        # Readiness
        resp = await client.get("/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ready"] is True
        assert data["dependencies"]["database"] == "ready"


@pytest.mark.asyncio
async def test_endpoint_lifecycle_via_rest():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Create Draft Endpoint (FR-001, FR-002, FR-003)
        create_payload = {
            "name": "Book Catalog API",
            "slug": "book-catalog",
            "target_url": "https://books.toscrape.com/",
            "schema_definition": {"title": "str", "price": "float"},
            "allowed_url_scope": ["https://books.toscrape.com/"],
        }
        res = await client.post("/api/v1/endpoints", json=create_payload)
        assert res.status_code == 201
        ep = res.json()
        endpoint_id = ep["endpoint_id"]
        assert ep["status"] == "DRAFT"
        assert ep["active_version_id"] is None
        assert "X-Correlation-ID" in res.headers

        # 2. List endpoints
        list_res = await client.get("/api/v1/endpoints")
        assert list_res.status_code == 200
        assert any(item["endpoint_id"] == endpoint_id for item in list_res.json())

        # 3. Get single endpoint
        get_res = await client.get(f"/api/v1/endpoints/{endpoint_id}")
        assert get_res.status_code == 200
        assert get_res.json()["slug"] == "book-catalog"

        # 4. Submit candidate selector configuration (from agent / user)
        candidate_payload = {
            "selector_map": {"title": "article.product_pod h3 a", "price": "p.price_color"},
            "rationale": "Selectors identified for book title and price",
        }
        cand_res = await client.post(f"/api/v1/endpoints/{endpoint_id}/candidates", json=candidate_payload)
        assert cand_res.status_code == 201
        cand_ver = cand_res.json()
        version_id = cand_ver["version_id"]
        assert cand_ver["status"] == "CANDIDATE"
        assert cand_ver["is_active"] is False

        # 5. Attempting to activate candidate BEFORE verification must fail with 422!
        activate_payload = {"version_id": version_id}
        bad_act = await client.post(f"/api/v1/endpoints/{endpoint_id}/activate", json=activate_payload)
        assert bad_act.status_code == 422
        assert "INVALID_CANDIDATE" in bad_act.json()["error_code"]

        # 6. Verify candidate with sample data
        verify_payload = {
            "sample_data": {"title": "A Light in the Attic", "price": "£51.77"}
        }
        ver_res = await client.post(f"/api/v1/endpoints/{endpoint_id}/candidates/{version_id}/verify", json=verify_payload)
        assert ver_res.status_code == 200
        ver_data = ver_res.json()
        assert ver_data["verified"] is True
        assert ver_data["status"] == "VERIFIED"
        assert ver_data["sample_data"]["price"] == 51.77

        # 7. Promote verified candidate to ACTIVE atomically
        good_act = await client.post(f"/api/v1/endpoints/{endpoint_id}/activate", json=activate_payload)
        assert good_act.status_code == 200
        active_ep = good_act.json()
        assert active_ep["status"] == "ACTIVE"
        assert active_ep["active_version_id"] == version_id

        # 8. Check audit trail
        audit_res = await client.get(f"/api/v1/endpoints/{endpoint_id}/audit")
        assert audit_res.status_code == 200
        audit_events = audit_res.json()["events"]
        actions = [a["action"] for a in audit_events]
        assert "ENDPOINT_CREATED" in actions
        assert "CANDIDATE_SUBMITTED" in actions
        assert "CANDIDATE_VERIFIED" in actions
        assert "VERSION_ACTIVATED" in actions
