import io
from unittest.mock import patch

from fastapi.testclient import TestClient


def test_document_metrics_empty(client: TestClient):
    response = client.get("/api/v1/metrics/documents")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 0
    assert set(payload.keys()) >= {
        "total",
        "pending",
        "processing",
        "ready",
        "failed",
        "total_size_bytes",
        "total_chunks",
    }


def test_processing_metrics_empty(client: TestClient):
    response = client.get("/api/v1/metrics/processing")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_jobs"] >= 0
    assert "failure_rate" in payload
    assert "by_stage" in payload
    assert isinstance(payload["by_stage"], list)


@patch("app.services.document_service.process_document_task.delay")
def test_document_metrics_after_upload(mock_delay, client: TestClient):
    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"
    upload = client.post(
        "/api/v1/documents/upload",
        files={"file": ("metrics.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload.status_code == 202

    response = client.get("/api/v1/metrics/documents")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 1
    assert payload["pending"] >= 1
    assert payload["total_size_bytes"] > 0
