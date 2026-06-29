"""Check Celery worker health and queue depth via Redis."""

import asyncio
import logging

from redis.asyncio import Redis

from app.config import get_settings

logger = logging.getLogger("app.worker_health")


async def get_worker_queue_depth() -> int:
    """Return the number of pending tasks in the Celery broker queue."""
    settings = get_settings()
    client = Redis.from_url(settings.redis_url)
    try:
        depth = await client.llen(settings.celery_queue_name)
        return int(depth or 0)
    except Exception:
        logger.warning("Failed to read worker queue depth from Redis", exc_info=True)
        return 0
    finally:
        await client.aclose()


async def check_worker() -> str:
    """Ping Celery workers and return ``"ok"`` or ``"error"``."""
    def ping_workers() -> bool:
        try:
            from app.workers.celery_app import celery_app

            responses = celery_app.control.ping(timeout=2.0)
            return bool(responses)
        except Exception:
            logger.warning("Worker ping failed", exc_info=True)
            return False

    return "ok" if await asyncio.to_thread(ping_workers) else "error"
