import logging

from redis.asyncio import Redis

from app.config import get_settings

logger = logging.getLogger("app.api_latency")

LATENCY_KEY = "metrics:api_latency_ms"
MAX_SAMPLES = 1000


async def record_api_latency(duration_ms: float) -> None:
    settings = get_settings()
    client = Redis.from_url(settings.redis_url)
    try:
        pipe = client.pipeline()
        pipe.lpush(LATENCY_KEY, str(round(duration_ms, 2)))
        pipe.ltrim(LATENCY_KEY, 0, MAX_SAMPLES - 1)
        await pipe.execute()
    except Exception:
        logger.debug("Failed to record API latency", exc_info=True)
    finally:
        await client.aclose()


async def get_api_latency_stats() -> tuple[float | None, int]:
    settings = get_settings()
    client = Redis.from_url(settings.redis_url)
    try:
        samples = await client.lrange(LATENCY_KEY, 0, -1)
    except Exception:
        logger.warning("Failed to read API latency stats from Redis", exc_info=True)
        return None, 0
    finally:
        await client.aclose()

    if not samples:
        return None, 0

    values: list[float] = []
    for item in samples:
        try:
            values.append(float(item))
        except (ValueError, TypeError):
            continue

    if not values:
        return None, 0

    avg = round(sum(values) / len(values), 2)
    return avg, len(values)
