import logging
from contextlib import asynccontextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import get_settings
from app.logging_config import configure_logging
from app.middleware import register_exception_handlers, register_middleware
from app.schemas.openapi_metadata import API_DESCRIPTION, OPENAPI_TAGS

logger = logging.getLogger("app.startup")


def run_migrations() -> None:
    alembic_ini = Path(__file__).resolve().parent.parent / "alembic.ini"
    alembic_cfg = Config(str(alembic_ini))
    command.upgrade(alembic_cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings
    try:
        run_migrations()
    except Exception:
        logger.exception("Database migration failed — app may be in an inconsistent state")
        raise
    logger.info("Application startup complete")
    yield
    logger.info("Application shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="Document Vault AI",
        description=API_DESCRIPTION,
        version="0.1.0",
        lifespan=lifespan,
        openapi_tags=OPENAPI_TAGS,
        contact={"name": "Document Vault AI", "url": "https://github.com/document-vault-ai"},
        license_info={"name": "MIT"},
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_middleware(app)
    register_exception_handlers(app)

    app.include_router(api_router, prefix="/api/v1")

    @app.get(
        "/",
        tags=["root"],
        summary="API entry point",
        description="Returns API name and links to interactive OpenAPI documentation.",
    )
    async def root() -> dict[str, str]:
        return {
            "message": "Document Vault AI API",
            "docs": "/docs",
            "openapi": "/openapi.json",
            "api_base": "/api/v1",
        }

    return app


app = create_app()
