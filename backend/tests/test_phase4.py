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
    assert "/api/v1/metrics/system" in paths


def test_openapi_upload_response_has_example(client: TestClient):
    response = client.get("/openapi.json")
    upload_post = response.json()["paths"]["/api/v1/documents/upload"]["post"]
    schema_ref = upload_post["responses"]["202"]["content"]["application/json"]["schema"]
    assert "$ref" in schema_ref or "example" in schema_ref


def test_openapi_endpoints_have_summaries(client: TestClient):
    schema = client.get("/openapi.json").json()
    paths = schema["paths"]
    expected_paths = [
        "/api/v1/documents/upload",
        "/api/v1/documents/upload/batch",
        "/api/v1/documents",
        "/api/v1/documents/{document_id}/status",
        "/api/v1/documents/{document_id}/insights",
        "/api/v1/chat/sessions",
        "/api/v1/chat/sessions/{session_id}/messages",
        "/api/v1/chat/sessions/{session_id}/messages/stream",
        "/api/v1/metrics/documents",
        "/api/v1/metrics/processing",
        "/api/v1/metrics/system",
        "/api/v1/health",
    ]
    for path in expected_paths:
        for method, operation in paths[path].items():
            assert operation.get("summary"), f"{method.upper()} {path} missing summary"
            assert operation.get("description"), f"{method.upper()} {path} missing description"


def test_openapi_streaming_has_sse_example(client: TestClient):
    stream_post = client.get("/openapi.json").json()["paths"][
        "/api/v1/chat/sessions/{session_id}/messages/stream"
    ]["post"]
    content = stream_post["responses"]["200"]["content"]["text/event-stream"]
    assert "token" in content["example"]
    assert "done" in content["example"]


def test_openapi_system_metrics_has_examples(client: TestClient):
    schema = client.get("/openapi.json").json()["components"]["schemas"]["SystemMetricsResponse"]
    assert schema["examples"]
    example = schema["examples"][0]
    assert "p95_api_latency_ms" in example
    assert "documents_per_hour" in example
    assert "chat" in example


def test_openapi_documents_upload_documents_error_responses(client: TestClient):
    upload_post = client.get("/openapi.json").json()["paths"]["/api/v1/documents/upload"]["post"]
    responses = upload_post["responses"]
    assert "400" in responses
    assert "429" in responses
    assert responses["400"]["content"]["application/json"]["example"]["error_code"]


def test_openapi_tags_documented(client: TestClient):
    tags = {tag["name"]: tag for tag in client.get("/openapi.json").json()["tags"]}
    assert "documents" in tags
    assert tags["documents"]["description"]
    assert tags["chat"]["description"]


def test_root_includes_api_links(client: TestClient):
    payload = client.get("/").json()
    assert payload["docs"] == "/docs"
    assert payload["openapi"] == "/openapi.json"
    assert payload["api_base"] == "/api/v1"
