from fastapi.testclient import TestClient

from app.main import app


def test_root():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "Document Vault AI API"


def test_health():
    client = TestClient(app)
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "document-vault-ai"
    assert data["api"] == "ok"
    assert data["status"] in {"ok", "degraded"}
    assert data["database"] in {"ok", "error"}
    assert data["redis"] in {"ok", "error"}
