import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy import text

from app.config import get_settings
from app.db.session import engine
from app.schemas.openapi_examples import HEALTH_EXAMPLE
from app.services.worker_health import check_worker

router = APIRouter()
logger = logging.getLogger("app.health")


async def _check_database() -> str:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        logger.exception("Database health check failed")
        return "error"


async def _check_redis() -> str:
    settings = get_settings()
    client = Redis.from_url(settings.redis_url)
    try:
        if await client.ping():
            return "ok"
        logger.warning("Redis ping returned falsy")
        return "error"
    except Exception:
        logger.exception("Redis health check failed")
        return "error"
    finally:
        await client.aclose()


@router.get(
    "/health",
    summary="Health check",
    response_description="Connectivity status for API, database, Redis, and Celery worker.",
    description=(
        "Verify API, database, Redis, and Celery worker connectivity. "
        "Returns `503` when any dependency is unhealthy (`status: degraded`)."
    ),
    responses={
        200: {"content": {"application/json": {"example": HEALTH_EXAMPLE}}},
        503: {
            "description": "One or more dependencies are unhealthy",
            "content": {
                "application/json": {
                    "example": {**HEALTH_EXAMPLE, "database": "error", "status": "degraded"}
                }
            },
        },
    },
)
async def health_check() -> JSONResponse:
    database = await _check_database()
    redis = await _check_redis()
    worker = await check_worker()
    is_healthy = database == "ok" and redis == "ok" and worker == "ok"

    checks = {
        "service": "document-vault-ai",
        "api": "ok",
        "database": database,
        "redis": redis,
        "worker": worker,
        "status": "ok" if is_healthy else "degraded",
    }

    return JSONResponse(content=checks, status_code=200 if is_healthy else 503)
