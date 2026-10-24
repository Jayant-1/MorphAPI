"""
Integration Test: End-to-End Prompt to Web API Generation and Extraction
Tests the primary user journey:
1. User supplies a natural language prompt with target URL https://sarthi.maharashtra.gov.in/en/government-resolution
2. MorphAPI synthesizes the endpoint, verifies selectors via Playwright, activates it, and returns endpoint URL and API key
3. User queries the returned endpoint URL with the API key and receives the 5 document links.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from morphapi.app import app
from morphapi.config import settings
from morphapi.db.migrations import run_migrations
from morphapi.services.endpoint_service import endpoint_service
from morphapi.services.extraction_service import shared_extraction_service


@pytest_asyncio.fixture(autouse=True)
async def init_test_db(tmp_path, monkeypatch):
    test_db = str(tmp_path / "test_prompt_flow.db")
    monkeypatch.setattr(settings, "db_path", test_db)
    endpoint_service.endpoint_repo.db_path = test_db
    endpoint_service.version_repo.db_path = test_db
    endpoint_service.auditor.repo.db_path = test_db
    shared_extraction_service.endpoint_repo.db_path = test_db
    shared_extraction_service.version_repo.db_path = test_db
    shared_extraction_service.auditor.repo.db_path = test_db
    await run_migrations(db_path=test_db)


@pytest.mark.asyncio
async def test_prompt_to_endpoint_and_query_flow():
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Step 1: User types the prompt on the MorphAPI page
        prompt_text = "Extract top 5 government resolution document links from https://sarthi.maharashtra.gov.in/en/government-resolution"
        gen_payload = {
            "prompt": prompt_text,
            "target_url": "https://sarthi.maharashtra.gov.in/en/government-resolution",
        }

        gen_resp = await client.post("/api/v1/endpoints/generate", json=gen_payload)
        assert gen_resp.status_code == 201, f"Generate failed: {gen_resp.text}"
        
        gen_data = gen_resp.json()
        assert "api_key" in gen_data
        assert "endpoint_url" in gen_data
        assert gen_data["status"] == "ACTIVE"
        assert gen_data["endpoint_url"] == "/api/v1/extract/sarthi-government-resolution"
        
        api_key = gen_data["api_key"]
        endpoint_url = gen_data["endpoint_url"]
        
        # Verify sample records were extracted
        assert "sample_data" in gen_data
        assert len(gen_data["sample_data"]) >= 5
        for doc in gen_data["sample_data"][:5]:
            link_val = doc.get("doc_link") or doc.get("link")
            assert link_val is not None
            assert link_val.startswith("https://")

        # Step 2: Query the endpoint directly via Fast Path
        query_resp = await client.get(
            f"{endpoint_url}?limit=5",
            headers={"X-API-Key": api_key},
        )
        assert query_resp.status_code == 200, f"Query failed: {query_resp.text}"
        
        extract_result = query_resp.json()
        assert extract_result["execution_path"] == "FAST_PATH"
        assert extract_result["healed_this_request"] is False
        
        docs = extract_result["data"]
        assert isinstance(docs, list)
        assert len(docs) == 5
        
        # Verify the top 5 documents have real links and details
        for i, doc in enumerate(docs):
            link_val = doc.get("doc_link") or doc.get("link")
            assert link_val is not None
            assert link_val.startswith("https://")
