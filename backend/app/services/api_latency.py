"""Record and query per-route API latency samples stored in Redis."""

import json
import logging
import re

from redis.asyncio import Redis

from app.config import get_settings
from app.schemas.metrics import RouteLatencyMetrics

logger = logging.getLogger("app.api_latency")

LATENCY_KEY = "metrics:api_latency_ms"
ROUTE_LATENCY_HASH = "metrics:api_latency_by_route"
MAX_SAMPLES = 1000
MAX_ROUTE_SAMPLES = 200

_UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)


def normalize_api_path(path: str) -> str:
    """Replace UUIDs in a URL path with ``{id}`` for route grouping."""
    return _UUID_RE.sub("{id}", path)


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    rank = (len(ordered) - 1) * percentile
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    interpolated = ordered[lower] + (ordered[upper] - ordered[lower]) * (rank - lower)
    return round(interpolated, 2)


def _parse_samples(raw_samples: list[str | bytes]) -> list[float]:
    values: list[float] = []
    for item in raw_samples:
        try:
            values.append(float(item))
        except (ValueError, TypeError):
            continue
    return values


async def record_api_latency(duration_ms: float, *, method: str, path: str) -> None:
    """Push a latency sample into the global and per-route Redis lists."""
    settings = get_settings()
    client = Redis.from_url(settings.redis_url)
    rounded = round(duration_ms, 2)
    route_key = f"{method.upper()} {normalize_api_path(path)}"
    try:
        existing_raw = await client.hget(ROUTE_LATENCY_HASH, route_key)
        route_samples: list[float] = []
        if existing_raw:
            try:
                route_samples = json.loads(existing_raw)
            except (json.JSONDecodeError, TypeError):
                route_samples = []

        route_samples.insert(0, rounded)
        route_samples = route_samples[:MAX_ROUTE_SAMPLES]

        pipe = client.pipeline()
        pipe.lpush(LATENCY_KEY, str(rounded))
        pipe.ltrim(LATENCY_KEY, 0, MAX_SAMPLES - 1)
        pipe.hset(ROUTE_LATENCY_HASH, route_key, json.dumps(route_samples))
        await pipe.execute()
    except Exception:
        logger.debug("Failed to record API latency", exc_info=True)
    finally:
        await client.aclose()


async def get_api_latency_stats() -> tuple[float | None, float | None, int, list[RouteLatencyMetrics]]:
    """Return avg latency, p95, sample count, and per-route breakdowns."""
    settings = get_settings()
    client = Redis.from_url(settings.redis_url)
    try:
        samples = await client.lrange(LATENCY_KEY, 0, -1)
        route_map = await client.hgetall(ROUTE_LATENCY_HASH)
    except Exception:
        logger.warning("Failed to read API latency stats from Redis", exc_info=True)
        return None, None, 0, []
    finally:
        await client.aclose()

    values = _parse_samples(samples)
    if not values:
        return None, None, 0, _build_route_metrics(route_map)

    avg = round(sum(values) / len(values), 2)
    p95 = _percentile(values, 0.95)
    return avg, p95, len(values), _build_route_metrics(route_map)


async def get_recent_api_latency_samples(limit: int = 60) -> list[float]:
    """Return recent latency samples oldest-first for sparkline charts."""
    settings = get_settings()
    client = Redis.from_url(settings.redis_url)
    try:
        samples = await client.lrange(LATENCY_KEY, 0, limit - 1)
    except Exception:
        logger.warning("Failed to read API latency samples from Redis", exc_info=True)
        return []
    finally:
        await client.aclose()

    values = _parse_samples(samples)
    values.reverse()
    return values


def _build_route_metrics(route_map: dict[bytes | str, bytes | str]) -> list[RouteLatencyMetrics]:
    metrics: list[RouteLatencyMetrics] = []
    for raw_route, raw_samples in route_map.items():
        route = raw_route.decode() if isinstance(raw_route, bytes) else raw_route
        payload = raw_samples.decode() if isinstance(raw_samples, bytes) else raw_samples
        try:
            samples = json.loads(payload)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(samples, list):
            continue
        values = [float(item) for item in samples if isinstance(item, (int, float))]
        if not values:
            continue
        metrics.append(
            RouteLatencyMetrics(
                route=route,
                avg_duration_ms=round(sum(values) / len(values), 2),
                p95_duration_ms=_percentile(values, 0.95),
                sample_count=len(values),
            )
        )
    return sorted(metrics, key=lambda item: (-item.sample_count, item.route))
