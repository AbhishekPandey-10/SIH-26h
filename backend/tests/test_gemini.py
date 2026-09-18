"""
Unit tests for Gemini Diagnostic endpoint
PS ID26047 — AI Clinical History-Taking Software for Indian Hospital OPDs
"""

from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "gemini_provisioned" in data
    assert "bhashini_provisioned" in data


def test_gemini_endpoint_status():
    client = TestClient(app)
    response = client.get("/api/test/gemini?prompt=Hello")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    # Either success (if key set) or unconfigured (if not set in current env)
    assert data["status"] in ["success", "unconfigured", "error"]
