"""Reusable OpenAPI response definitions for consistent API documentation."""

from app.schemas.openapi_examples import (
    ERROR_BAD_GATEWAY_EXAMPLE,
    ERROR_BAD_REQUEST_EXAMPLE,
    ERROR_CONFLICT_EXAMPLE,
    ERROR_NOT_FOUND_EXAMPLE,
    ERROR_RATE_LIMIT_EXAMPLE,
    ERROR_VALIDATION_EXAMPLE,
)


def _json_response(description: str, example: dict) -> dict:
    return {
        "description": description,
        "content": {"application/json": {"example": example}},
    }


def error_responses(*status_examples: tuple[int, str, dict]) -> dict[int, dict]:
    return {status: _json_response(description, example) for status, description, example in status_examples}


RESPONSE_400 = error_responses((400, "Invalid request", ERROR_BAD_REQUEST_EXAMPLE))
RESPONSE_404 = error_responses((404, "Resource not found", ERROR_NOT_FOUND_EXAMPLE))
RESPONSE_409 = error_responses((409, "Resource not in the required state", ERROR_CONFLICT_EXAMPLE))
RESPONSE_422 = error_responses((422, "Request validation failed", ERROR_VALIDATION_EXAMPLE))
RESPONSE_429 = error_responses((429, "Rate limit exceeded", ERROR_RATE_LIMIT_EXAMPLE))
RESPONSE_502 = error_responses((502, "Upstream AI service error", ERROR_BAD_GATEWAY_EXAMPLE))


def merge_responses(*response_maps: dict[int, dict]) -> dict[int, dict]:
    merged: dict[int, dict] = {}
    for response_map in response_maps:
        merged.update(response_map)
    return merged


DOCUMENT_READ_RESPONSES = merge_responses(RESPONSE_404)
DOCUMENT_INSIGHTS_RESPONSES = merge_responses(RESPONSE_404, RESPONSE_409)
CHAT_SESSION_RESPONSES = merge_responses(RESPONSE_404)
CHAT_MESSAGE_RESPONSES = merge_responses(RESPONSE_404, RESPONSE_409, RESPONSE_502)
UPLOAD_RESPONSES = merge_responses(RESPONSE_400, RESPONSE_429)
