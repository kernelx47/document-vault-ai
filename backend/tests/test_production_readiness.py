from unittest.mock import patch

from fastapi.testclient import TestClient

from app.services.ai_usage_service import record_ai_usage_sync


def test_ai_usage_metrics_endpoint(client: TestClient):
    record_ai_usage_sync(
        operation="chat",
        provider="openai",
        model="gpt-4o-mini",
        input_tokens=100,
        output_tokens=50,
    )
    response = client.get("/api/v1/metrics/ai-usage")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_requests"] >= 1
    assert payload["total_input_tokens"] >= 100
    assert "estimated_cost_usd" in payload
    assert "by_operation" in payload


def test_health_live(client: TestClient):
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


def test_health_ready(client: TestClient):
    response = client.get("/api/v1/health/ready")
    assert response.status_code in (200, 503)
    assert "database" in response.json()


def test_request_id_header(client: TestClient):
    response = client.get("/api/v1/health/live", headers={"X-Request-ID": "test-req-123"})
    assert response.headers.get("X-Request-ID") == "test-req-123"


@patch("app.services.document_service.process_document_task.delay")
def test_document_version_upload(mock_delay, client: TestClient):
    import io

    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"
    upload = client.post(
        "/api/v1/documents/upload",
        files={"file": ("v1.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload.status_code == 202
    doc_id = upload.json()["id"]

    version = client.post(
        f"/api/v1/documents/{doc_id}/versions",
        files={"file": ("v2.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert version.status_code == 202

    versions = client.get(f"/api/v1/documents/{doc_id}/versions")
    assert versions.status_code == 200
    payload = versions.json()
    assert payload["total"] == 2
    assert payload["items"][0]["version_number"] == 2
    assert payload["items"][0]["is_latest"] is True
