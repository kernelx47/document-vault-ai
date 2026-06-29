from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.schemas.metrics import SystemMetricsResponse


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


def test_system_metrics_endpoint(client: TestClient):
    sample = SystemMetricsResponse(
        avg_api_latency_ms=25.0,
        api_request_samples=10,
        worker_queue_depth=1,
        documents_per_hour=3,
        document_failure_rate=0.0,
        processing_failure_rate=0.05,
        avg_processing_duration_ms=500.0,
        stage_avg_duration_ms=[],
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
    assert payload["worker_queue_depth"] == 1
    assert "processing_failure_rate" in payload
