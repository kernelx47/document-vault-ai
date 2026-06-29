"""Record and aggregate chat/RAG request metrics in Redis."""

import json
import logging

from redis.asyncio import Redis

from app.config import get_settings

logger = logging.getLogger("app.rag_metrics")

CHAT_SAMPLES_KEY = "metrics:chat_samples"
MAX_CHAT_SAMPLES = 500


async def record_chat_request(
    *,
    duration_ms: float,
    retrieval_ms: float | None,
    success: bool,
) -> None:
    """Push a chat request timing sample to Redis."""
    settings = get_settings()
    client = Redis.from_url(settings.redis_url)
    payload = json.dumps(
        {
            "duration_ms": round(duration_ms, 2),
            "retrieval_ms": round(retrieval_ms, 2) if retrieval_ms is not None else None,
            "success": success,
        }
    )
    try:
        pipe = client.pipeline()
        pipe.lpush(CHAT_SAMPLES_KEY, payload)
        pipe.ltrim(CHAT_SAMPLES_KEY, 0, MAX_CHAT_SAMPLES - 1)
        await pipe.execute()
    except Exception:
        logger.debug("Failed to record chat metrics", exc_info=True)
    finally:
        await client.aclose()


async def get_chat_metrics() -> tuple[int, int, float, float | None, float | None]:
    """Return total samples, errors, error rate, avg RAG ms, avg retrieval ms."""
    settings = get_settings()
    client = Redis.from_url(settings.redis_url)
    try:
        samples = await client.lrange(CHAT_SAMPLES_KEY, 0, -1)
    except Exception:
        logger.warning("Failed to read chat metrics from Redis", exc_info=True)
        return 0, 0, 0.0, None, None
    finally:
        await client.aclose()

    if not samples:
        return 0, 0, 0.0, None, None

    durations: list[float] = []
    retrieval_durations: list[float] = []
    errors = 0
    for item in samples:
        try:
            entry = json.loads(item)
        except (json.JSONDecodeError, TypeError):
            continue
        if not entry.get("success", True):
            errors += 1
        duration = entry.get("duration_ms")
        if isinstance(duration, (int, float)):
            durations.append(float(duration))
        retrieval = entry.get("retrieval_ms")
        if isinstance(retrieval, (int, float)):
            retrieval_durations.append(float(retrieval))

    total = len(durations)
    error_rate = round(errors / total, 4) if total else 0.0
    avg_rag = round(sum(durations) / len(durations), 2) if durations else None
    avg_retrieval = (
        round(sum(retrieval_durations) / len(retrieval_durations), 2)
        if retrieval_durations
        else None
    )
    return total, errors, error_rate, avg_rag, avg_retrieval
