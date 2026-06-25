import io
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.exceptions import APIError


def test_not_found_includes_error_code(client: TestClient):
    response = client.get("/api/v1/documents/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    payload = response.json()
    assert payload["detail"] == "Document not found."
    assert payload["error_code"] == "NOT_FOUND"


def test_validation_error_includes_error_code(client: TestClient):
    response = client.post("/api/v1/documents/upload")
    assert response.status_code == 422
    payload = response.json()
    assert payload["error_code"] == "VALIDATION_ERROR"
    assert "errors" in payload


@patch("app.api.v1.documents.enforce_upload_rate_limit", new_callable=AsyncMock)
def test_upload_rate_limit_returns_error_code(mock_rate_limit, client: TestClient):
    mock_rate_limit.side_effect = APIError(
        status_code=429,
        detail="Upload rate limit exceeded. Maximum 30 uploads per minute.",
        error_code="RATE_LIMIT_EXCEEDED",
    )
    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("sample.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert response.status_code == 429
    payload = response.json()
    assert payload["error_code"] == "RATE_LIMIT_EXCEEDED"
