import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.exceptions import (
    api_error_handler,
    starlette_http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.middleware.request_logging import RequestLoggingMiddleware

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(HTTPException, api_error_handler)
    app.add_exception_handler(StarletteHTTPException, starlette_http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)


def register_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def log_unhandled_errors(request: Request, call_next):
        try:
            return await call_next(request)
        except HTTPException:
            raise
        except Exception:
            logger.exception(
                "unhandled exception",
                extra={"method": request.method, "path": request.url.path},
            )
            raise

    app.add_middleware(RequestLoggingMiddleware)
