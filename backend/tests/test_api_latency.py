from app.services.api_latency import _percentile, normalize_api_path


def test_normalize_api_path_replaces_uuid():
    path = "/api/v1/documents/550e8400-e29b-41d4-a716-446655440000/status"
    assert normalize_api_path(path) == "/api/v1/documents/{id}/status"


def test_percentile_empty():
    assert _percentile([], 0.95) is None


def test_percentile_single_value():
    assert _percentile([42.0], 0.95) == 42.0


def test_percentile_multiple_values():
    values = [10.0, 20.0, 30.0, 40.0, 100.0]
    assert _percentile(values, 0.95) == 88.0
