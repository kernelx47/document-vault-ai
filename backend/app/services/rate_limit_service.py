from redis.asyncio import Redis

from app.config import get_settings
from app.exceptions import APIError


async def enforce_upload_rate_limit(client_ip: str) -> None:
    settings = get_settings()
    if settings.upload_rate_limit_per_minute <= 0:
        return

    redis = Redis.from_url(settings.redis_url)
    key = f"rate_limit:upload:{client_ip}"
    try:
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, 60)
        if count > settings.upload_rate_limit_per_minute:
            raise APIError(
                status_code=429,
                detail=(
                    f"Upload rate limit exceeded. "
                    f"Maximum {settings.upload_rate_limit_per_minute} uploads per minute."
                ),
                error_code="RATE_LIMIT_EXCEEDED",
            )
    finally:
        await redis.aclose()
