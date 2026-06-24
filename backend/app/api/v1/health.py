from fastapi import APIRouter
from redis.asyncio import Redis
from sqlalchemy import text

from app.config import get_settings
from app.db.session import engine

router = APIRouter()


async def _check_database() -> str:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        return "error"


async def _check_redis() -> str:
    settings = get_settings()
    client = Redis.from_url(settings.redis_url)
    try:
        if await client.ping():
            return "ok"
        return "error"
    except Exception:
        return "error"
    finally:
        await client.aclose()


@router.get("/health")
async def health_check() -> dict[str, str]:
    database = await _check_database()
    redis = await _check_redis()
    checks = {
        "service": "document-vault-ai",
        "api": "ok",
        "database": database,
        "redis": redis,
    }
    checks["status"] = "ok" if database == "ok" and redis == "ok" else "degraded"
    return checks
