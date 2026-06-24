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
