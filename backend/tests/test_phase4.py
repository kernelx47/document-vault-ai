from pathlib import Path

from fastapi.testclient import TestClient


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_demo_script_exists_and_is_valid_bash():
    demo = REPO_ROOT / "scripts" / "demo.sh"
    assert demo.is_file()
    assert demo.stat().st_mode & 0o111
    content = demo.read_text(encoding="utf-8")
    assert "metrics/documents" in content
    assert "chat/sessions" in content


def test_sample_pdf_fixture_exists():
    fixture = REPO_ROOT / "backend" / "tests" / "fixtures" / "sample.pdf"
    assert fixture.is_file()
    assert fixture.read_bytes().startswith(b"%PDF")


def test_openapi_docs_available(client: TestClient):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    paths = schema.get("paths", {})
    assert "/api/v1/documents/upload" in paths
    assert "/api/v1/chat/sessions/{session_id}/messages" in paths
    assert "/api/v1/metrics/documents" in paths


def test_openapi_upload_response_has_example(client: TestClient):
    response = client.get("/openapi.json")
    upload_post = response.json()["paths"]["/api/v1/documents/upload"]["post"]
    schema_ref = upload_post["responses"]["202"]["content"]["application/json"]["schema"]
    assert "$ref" in schema_ref or "example" in schema_ref
