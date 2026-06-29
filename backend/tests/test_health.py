from fastapi.testclient import TestClient


def test_root(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "Document Vault AI API"


def test_health(client: TestClient):
    response = client.get("/api/v1/health")
    assert response.status_code in {200, 503}
    data = response.json()
    assert data["service"] == "document-vault-ai"
    assert data["api"] == "ok"
    assert data["status"] in {"ok", "degraded"}
    assert data["database"] in {"ok", "error"}
    assert data["redis"] in {"ok", "error"}
    assert data["worker"] in {"ok", "error"}
    if data["status"] == "ok":
        assert response.status_code == 200
    else:
        assert response.status_code == 503
