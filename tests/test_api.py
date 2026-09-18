import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings

client = TestClient(app)
AUTH_HEADERS = {"X-API-Key": settings.API_KEY}
BEARER_HEADERS = {"Authorization": f"Bearer {settings.API_KEY}"}


def test_health_and_metrics():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"

    res = client.get("/metrics")
    assert res.status_code == 200
    metrics = res.json()
    assert "uptime_seconds" in metrics


def test_unauthenticated_and_invalid_auth():
    # No auth
    res = client.post("/v1/retrieve", json={"knowledgeBaseId": "engineering_docs", "query": "test"})
    assert res.status_code == 401

    res = client.get("/v1/sync/status")
    assert res.status_code == 401

    # Invalid API key
    res = client.post(
        "/v1/retrieve",
        json={"knowledgeBaseId": "engineering_docs", "query": "test"},
        headers={"X-API-Key": "wrong-key"},
    )
    assert res.status_code == 401

    # Invalid Bearer token
    res = client.post(
        "/v1/retrieve",
        json={"knowledgeBaseId": "engineering_docs", "query": "test"},
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert res.status_code == 401


def test_authenticated_retrieval_and_copilot_endpoint():
    payload = {
        "knowledgeBaseId": "engineering_docs",
        "query": "important details",
        "maxResults": 5,
    }

    # Test with X-API-Key header
    res = client.post("/v1/retrieve", json=payload, headers=AUTH_HEADERS)
    assert res.status_code == 200
    data = res.json()
    assert data["knowledgeBaseId"] == "engineering_docs"
    assert "chunks" in data

    # Test with Bearer auth
    res_bearer = client.post("/v1/retrieve", json=payload, headers=BEARER_HEADERS)
    assert res_bearer.status_code == 200
    assert res_bearer.json()["knowledgeBaseId"] == "engineering_docs"

    res = client.post("/v1/test/copilot", json=payload, headers=AUTH_HEADERS)
    assert res.status_code == 200
    copilot_data = res.json()
    assert copilot_data["status"] == "success"
    assert "copilot_grounding_payload" in copilot_data


def test_sync_trigger_and_status():
    res = client.post("/v1/sync/trigger", headers=AUTH_HEADERS)
    assert res.status_code == 200
    sync_res = res.json()
    assert "status" in sync_res

    res = client.get("/v1/sync/status", headers=AUTH_HEADERS)
    assert res.status_code == 200
    status_data = res.json()
    assert "status" in status_data
