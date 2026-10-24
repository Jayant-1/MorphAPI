"""
End-to-End Tests for MorphAPI V2 API
"""

import pytest
from httpx import AsyncClient, ASGITransport
from morphapi_v2.api.app import app
from morphapi_v2.db.repository import endpoint_repo_v2


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/v2/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        assert resp.json()["version"] == "2.0.0"


@pytest.mark.asyncio
async def test_db_repository_isolation(tmp_path):
    test_db = tmp_path / "test_v2.db"
    endpoint_repo_v2.db_path = str(test_db)

    await endpoint_repo_v2.save_endpoint(
        endpoint_id="ep_v2_test123",
        user_id="alice",
        api_name="test-api",
        slug="test-api",
        target_url="https://example.com/items",
        schema_definition={"title": "str", "price": "float"},
        inputs={},
        plan={"strategy": "hierarchical_dom", "container_selector": "div.card"},
        sample_data=[{"title": "Item 1", "price": 9.99}],
        api_key="mapik_test_123",
    )

    loaded = await endpoint_repo_v2.get_endpoint("alice", "test-api")
    assert loaded is not None
    assert loaded["api_name"] == "test-api"
    assert loaded["schema_definition"] == {"title": "str", "price": "float"}
    assert len(loaded["sample_data"]) == 1

    # Query via REST API
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Check endpoints list
        list_resp = await client.get("/v2/endpoints")
        assert list_resp.status_code == 200
        items = list_resp.json()
        assert len(items) >= 1
        assert items[0]["slug"] == "test-api"
