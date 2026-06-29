import io
from unittest.mock import patch


@patch("app.services.document_service.process_document_task.delay")
def test_upload_pdf_queues_processing(mock_delay, client):
    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("sample.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert response.status_code == 202
    payload = response.json()
    assert payload["filename"] == "sample.pdf"
    assert payload["status"] == "pending"
    mock_delay.assert_called_once()


def test_list_documents_empty(client):
    response = client.get("/api/v1/documents")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload["items"], list)
    assert payload["total"] >= 0


def test_upload_rejects_unsupported_type(client):
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("notes.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert response.status_code == 400


@patch("app.services.document_service.process_document_task.delay")
def test_batch_upload_queues_multiple_files(mock_delay, client):
    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"
    response = client.post(
        "/api/v1/documents/upload/batch",
        files=[
            ("files", ("a.pdf", io.BytesIO(pdf_bytes), "application/pdf")),
            ("files", ("b.pdf", io.BytesIO(pdf_bytes), "application/pdf")),
        ],
    )
    assert response.status_code == 202
    payload = response.json()
    assert payload["queued_count"] == 2
    assert len(payload["accepted"]) == 2
    assert payload["failed_count"] == 0
    assert mock_delay.call_count == 2


@patch("app.services.document_service.process_document_task.delay")
def test_batch_upload_returns_partial_failures(mock_delay, client):
    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"
    response = client.post(
        "/api/v1/documents/upload/batch",
        files=[
            ("files", ("good.pdf", io.BytesIO(pdf_bytes), "application/pdf")),
            ("files", ("bad.txt", io.BytesIO(b"hello"), "text/plain")),
        ],
    )
    assert response.status_code == 202
    payload = response.json()
    assert payload["queued_count"] == 1
    assert payload["failed_count"] == 1
    assert mock_delay.call_count == 1


def test_batch_upload_rejects_empty_list(client):
    response = client.post("/api/v1/documents/upload/batch", files=[])
    assert response.status_code == 422


@patch("app.services.document_service.process_document_task.delay")
def test_batch_upload_creates_batch_with_id(mock_delay, client):
    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"
    response = client.post(
        "/api/v1/documents/upload/batch",
        files=[("files", ("x.pdf", io.BytesIO(pdf_bytes), "application/pdf"))],
    )
    assert response.status_code == 202
    payload = response.json()
    assert payload["batch_id"] is not None

    batch_resp = client.get(f"/api/v1/documents/batches/{payload['batch_id']}")
    assert batch_resp.status_code == 200
    batch = batch_resp.json()
    assert batch["total_files"] == 1
    assert len(batch["documents"]) == 1


def test_list_batches_returns_paginated(client):
    response = client.get("/api/v1/documents/batches")
    assert response.status_code == 200
    payload = response.json()
    assert "items" in payload
    assert "total" in payload
    assert isinstance(payload["items"], list)


def test_get_batch_not_found(client):
    response = client.get("/api/v1/documents/batches/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
