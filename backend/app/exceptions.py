from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

STATUS_ERROR_CODES: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMIT_EXCEEDED",
    500: "INTERNAL_ERROR",
}


class APIError(HTTPException):
    def __init__(self, status_code: int, detail: str, error_code: str):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code


def _error_code_for_status(status_code: int) -> str:
    return STATUS_ERROR_CODES.get(status_code, "HTTP_ERROR")


def _format_detail(detail: object) -> str:
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list):
        return "Request validation failed."
    return str(detail)


async def api_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    error_code = getattr(exc, "error_code", None) or _error_code_for_status(exc.status_code)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": _format_detail(exc.detail), "error_code": error_code},
    )


async def starlette_http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    error_code = _error_code_for_status(exc.status_code)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": _format_detail(exc.detail), "error_code": error_code},
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Request validation failed.",
            "error_code": "VALIDATION_ERROR",
            "errors": exc.errors(),
        },
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An unexpected error occurred.",
            "error_code": "INTERNAL_ERROR",
        },
    )
