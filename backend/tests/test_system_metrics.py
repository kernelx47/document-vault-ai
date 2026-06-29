from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.schemas.metrics import ChatMetrics, SystemMetricsResponse


def test_health_includes_worker(client: TestClient):
    with (
        patch("app.api.v1.health.check_worker", new_callable=AsyncMock, return_value="ok"),
        patch("app.api.v1.health._check_database", new_callable=AsyncMock, return_value="ok"),
        patch("app.api.v1.health._check_redis", new_callable=AsyncMock, return_value="ok"),
    ):
        response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "worker" in data
    assert data["worker"] == "ok"


def test_health_degraded_returns_503(client: TestClient):
    with (
        patch("app.api.v1.health.check_worker", new_callable=AsyncMock, return_value="error"),
        patch("app.api.v1.health._check_database", new_callable=AsyncMock, return_value="ok"),
        patch("app.api.v1.health._check_redis", new_callable=AsyncMock, return_value="ok"),
    ):
        response = client.get("/api/v1/health")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "degraded"


def test_openapi_health_has_typed_schema(client: TestClient):
    schema = client.get("/openapi.json").json()
    health_get = schema["paths"]["/api/v1/health"]["get"]
    assert health_get["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "HealthResponse"
    )


def test_system_metrics_endpoint(client: TestClient):
    sample = SystemMetricsResponse(
        avg_api_latency_ms=25.0,
        p95_api_latency_ms=80.0,
        api_request_samples=10,
        api_latency_by_route=[],
        worker_queue_depth=1,
        documents_processed_per_hour=3,
        document_failure_rate=0.0,
        processing_failure_rate=0.05,
        avg_processing_duration_ms=500.0,
        stage_avg_duration_ms=[],
        chat=ChatMetrics(
            total_requests=5,
            error_count=1,
            error_rate=0.2,
            avg_rag_duration_ms=900.0,
            avg_retrieval_duration_ms=110.0,
        ),
    )
    with patch(
        "app.api.v1.metrics.metrics_service.get_system_metrics",
        new_callable=AsyncMock,
        return_value=sample,
    ):
        response = client.get("/api/v1/metrics/system")
    assert response.status_code == 200
    payload = response.json()
    assert payload["avg_api_latency_ms"] == 25.0
    assert payload["p95_api_latency_ms"] == 80.0
    assert payload["worker_queue_depth"] == 1
    assert payload["documents_processed_per_hour"] == 3
    assert payload["chat"]["avg_rag_duration_ms"] == 900.0
