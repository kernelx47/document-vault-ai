"""Track AI API token usage, estimated costs, and daily quotas via Redis."""

import json
import logging
from datetime import UTC, datetime, timedelta

from redis import Redis

from app.config import get_settings

logger = logging.getLogger("app.ai_usage")

USAGE_SAMPLES_KEY = "metrics:ai_usage_samples"
DAILY_REQUESTS_KEY = "quota:ai_requests"
MAX_USAGE_SAMPLES = 2000


def estimate_tokens(text: str) -> int:
    """Return a rough token count (~4 chars per token)."""
    cleaned = text.strip()
    if not cleaned:
        return 0
    return max(1, len(cleaned) // 4)


def _estimate_cost_usd(
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> float:
    settings = get_settings()
    if provider == "openai":
        input_rate = settings.openai_input_cost_per_1m_tokens
        output_rate = settings.openai_output_cost_per_1m_tokens
    elif provider == "gemini":
        input_rate = settings.gemini_input_cost_per_1m_tokens
        output_rate = settings.gemini_output_cost_per_1m_tokens
    else:
        return 0.0
    cost = (input_tokens / 1_000_000 * input_rate) + (output_tokens / 1_000_000 * output_rate)
    return round(cost, 6)


def record_ai_usage_sync(
    *,
    operation: str,
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> None:
    """Persist a single AI usage sample to Redis (synchronous)."""
    settings = get_settings()
    client = Redis.from_url(settings.redis_url, decode_responses=True)
    payload = json.dumps(
        {
            "operation": operation,
            "provider": provider,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "estimated_cost_usd": _estimate_cost_usd(provider, model, input_tokens, output_tokens),
            "recorded_at": datetime.now(UTC).isoformat(),
        }
    )
    try:
        pipe = client.pipeline()
        pipe.lpush(USAGE_SAMPLES_KEY, payload)
        pipe.ltrim(USAGE_SAMPLES_KEY, 0, MAX_USAGE_SAMPLES - 1)
        if settings.daily_ai_request_quota > 0:
            day_key = f"{DAILY_REQUESTS_KEY}:{datetime.now(UTC).strftime('%Y-%m-%d')}"
            pipe.incr(day_key)
            pipe.expire(day_key, 172800)
        pipe.execute()
    except Exception:
        logger.debug("Failed to record AI usage", exc_info=True)
    finally:
        client.close()


async def get_daily_ai_request_count() -> int:
    """Return today's AI request count from Redis."""
    settings = get_settings()
    from redis.asyncio import Redis as AsyncRedis

    client = AsyncRedis.from_url(settings.redis_url, decode_responses=True)
    day_key = f"{DAILY_REQUESTS_KEY}:{datetime.now(UTC).strftime('%Y-%m-%d')}"
    try:
        value = await client.get(day_key)
        return int(value or 0)
    except Exception:
        logger.warning("Failed to read daily AI quota usage", exc_info=True)
        return 0
    finally:
        await client.aclose()


async def get_ai_usage_timeseries(hours: int = 24) -> list[dict]:
    """Bucket AI usage samples by hour for dashboard sparklines."""
    from redis.asyncio import Redis as AsyncRedis

    settings = get_settings()
    client = AsyncRedis.from_url(settings.redis_url, decode_responses=True)
    try:
        samples = await client.lrange(USAGE_SAMPLES_KEY, 0, -1)
    except Exception:
        logger.warning("Failed to read AI usage timeseries", exc_info=True)
        return []
    finally:
        await client.aclose()

    cutoff = datetime.now(UTC) - timedelta(hours=hours)
    buckets: dict[str, dict] = {}

    for item in samples:
        try:
            entry = json.loads(item)
        except (json.JSONDecodeError, TypeError):
            continue

        recorded_raw = entry.get("recorded_at")
        if not recorded_raw:
            continue
        try:
            recorded_at = datetime.fromisoformat(str(recorded_raw).replace("Z", "+00:00"))
        except ValueError:
            continue
        if recorded_at < cutoff:
            continue

        bucket_key = recorded_at.strftime("%Y-%m-%dT%H:00")
        label = recorded_at.strftime("%b %d %H:00")
        bucket = buckets.setdefault(
            bucket_key,
            {"label": label, "requests": 0, "tokens": 0, "cost_usd": 0.0},
        )
        input_tokens = int(entry.get("input_tokens", 0))
        output_tokens = int(entry.get("output_tokens", 0))
        bucket["requests"] += 1
        bucket["tokens"] += input_tokens + output_tokens
        bucket["cost_usd"] = round(bucket["cost_usd"] + float(entry.get("estimated_cost_usd", 0)), 6)

    return [buckets[key] for key in sorted(buckets.keys())]


async def get_ai_usage_metrics() -> dict:
    """Aggregate AI usage samples by operation and provider."""
    from redis.asyncio import Redis as AsyncRedis

    settings = get_settings()
    client = AsyncRedis.from_url(settings.redis_url, decode_responses=True)
    try:
        samples = await client.lrange(USAGE_SAMPLES_KEY, 0, -1)
    except Exception:
        logger.warning("Failed to read AI usage metrics", exc_info=True)
        return _empty_metrics()
    finally:
        await client.aclose()

    if not samples:
        return _empty_metrics()

    total_requests = 0
    total_input_tokens = 0
    total_output_tokens = 0
    total_cost_usd = 0.0
    by_operation: dict[str, dict] = {}
    by_provider: dict[str, dict] = {}

    for item in samples:
        try:
            entry = json.loads(item)
        except (json.JSONDecodeError, TypeError):
            continue
        total_requests += 1
        input_tokens = int(entry.get("input_tokens", 0))
        output_tokens = int(entry.get("output_tokens", 0))
        cost = float(entry.get("estimated_cost_usd", 0))
        total_input_tokens += input_tokens
        total_output_tokens += output_tokens
        total_cost_usd += cost

        operation = str(entry.get("operation", "unknown"))
        op_bucket = by_operation.setdefault(
            operation,
            {"operation": operation, "requests": 0, "input_tokens": 0, "output_tokens": 0, "estimated_cost_usd": 0.0},
        )
        op_bucket["requests"] += 1
        op_bucket["input_tokens"] += input_tokens
        op_bucket["output_tokens"] += output_tokens
        op_bucket["estimated_cost_usd"] = round(op_bucket["estimated_cost_usd"] + cost, 6)

        provider = str(entry.get("provider", "unknown"))
        prov_bucket = by_provider.setdefault(
            provider,
            {"provider": provider, "requests": 0, "input_tokens": 0, "output_tokens": 0, "estimated_cost_usd": 0.0},
        )
        prov_bucket["requests"] += 1
        prov_bucket["input_tokens"] += input_tokens
        prov_bucket["output_tokens"] += output_tokens
        prov_bucket["estimated_cost_usd"] = round(prov_bucket["estimated_cost_usd"] + cost, 6)

    daily_count = await get_daily_ai_request_count()
    quota_remaining = None
    if settings.daily_ai_request_quota > 0:
        quota_remaining = max(settings.daily_ai_request_quota - daily_count, 0)

    return {
        "total_requests": total_requests,
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "estimated_cost_usd": round(total_cost_usd, 4),
        "daily_request_count": daily_count,
        "daily_request_quota": settings.daily_ai_request_quota or None,
        "daily_quota_remaining": quota_remaining,
        "by_operation": sorted(by_operation.values(), key=lambda item: item["operation"]),
        "by_provider": sorted(by_provider.values(), key=lambda item: item["provider"]),
    }


def _empty_metrics() -> dict:
    settings = get_settings()
    return {
        "total_requests": 0,
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "estimated_cost_usd": 0.0,
        "daily_request_count": 0,
        "daily_request_quota": settings.daily_ai_request_quota or None,
        "daily_quota_remaining": settings.daily_ai_request_quota or None,
        "by_operation": [],
        "by_provider": [],
    }
