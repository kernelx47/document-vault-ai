import logging
from datetime import UTC, datetime

from redis.asyncio import Redis

from app.config import get_settings
from app.exceptions import APIError
from app.services.ai_usage_service import get_daily_ai_request_count

logger = logging.getLogger("app.rate_limit")


async def _increment_rate_limit(redis: Redis, key: str, ttl_seconds: int, limit: int, detail: str) -> None:
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, ttl_seconds)
    if count > limit:
        raise APIError(status_code=429, detail=detail, error_code="RATE_LIMIT_EXCEEDED")


async def enforce_upload_rate_limit(client_ip: str) -> None:
    settings = get_settings()
    if settings.upload_rate_limit_per_minute <= 0:
        return

    try:
        redis = Redis.from_url(settings.redis_url)
    except Exception:
        logger.warning("Redis unavailable for rate limiting — failing open", exc_info=True)
        return

    key = f"rate_limit:upload:{client_ip}"
    try:
        await _increment_rate_limit(
            redis,
            key,
            60,
            settings.upload_rate_limit_per_minute,
            (
                f"Upload rate limit exceeded. "
                f"Maximum {settings.upload_rate_limit_per_minute} uploads per minute."
            ),
        )
    except APIError:
        raise
    except Exception:
        logger.warning("Rate limit check failed — failing open", exc_info=True)
    finally:
        await redis.aclose()


async def enforce_chat_rate_limit(client_ip: str) -> None:
    settings = get_settings()
    if settings.chat_rate_limit_per_minute <= 0:
        return

    try:
        redis = Redis.from_url(settings.redis_url)
    except Exception:
        logger.warning("Redis unavailable for chat rate limiting — failing open", exc_info=True)
        return

    key = f"rate_limit:chat:{client_ip}"
    try:
        await _increment_rate_limit(
            redis,
            key,
            60,
            settings.chat_rate_limit_per_minute,
            (
                f"Chat rate limit exceeded. "
                f"Maximum {settings.chat_rate_limit_per_minute} messages per minute."
            ),
        )
    except APIError:
        raise
    except Exception:
        logger.warning("Chat rate limit check failed — failing open", exc_info=True)
    finally:
        await redis.aclose()


async def enforce_daily_ai_quota() -> None:
    settings = get_settings()
    if settings.daily_ai_request_quota <= 0:
        return

    try:
        daily_count = await get_daily_ai_request_count()
    except Exception:
        logger.warning("Daily AI quota check failed — failing open", exc_info=True)
        return

    if daily_count >= settings.daily_ai_request_quota:
        raise APIError(
            status_code=429,
            detail=(
                f"Daily AI request quota exceeded. "
                f"Limit is {settings.daily_ai_request_quota} requests per day "
                f"({datetime.now(UTC).strftime('%Y-%m-%d')} UTC)."
            ),
            error_code="QUOTA_EXCEEDED",
        )
