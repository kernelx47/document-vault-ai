"""OpenAPI metadata shared by the FastAPI application."""

API_DESCRIPTION = """
Upload PDF or DOCX documents, wait for async processing, then chat with your documents using RAG with citations.

## Typical workflow

1. **Upload** — `POST /documents/upload` returns `202` with a document ID (`status: pending`).
2. **Poll status** — `GET /documents/{id}/status` until `status` is `ready` (or `failed`).
3. **Insights** — `GET /documents/{id}/insights` for AI summary and bullet points.
4. **Chat** — `POST /documents/{id}/chat/sessions`, then `POST /chat/sessions/{id}/messages`.
5. **Monitor** — `GET /metrics/system`, `GET /metrics/documents`, `GET /metrics/storage`, and `GET /health` for operational visibility.

## Authentication

This API is open for local/demo use. No authentication headers are required. Do not expose it publicly without adding auth, TLS, and rate limits appropriate to your environment.

## Document status lifecycle

| Status | Meaning |
|--------|---------|
| `pending` | Queued for background processing |
| `processing` | Worker is extracting, chunking, and embedding |
| `ready` | Available for insights and chat |
| `failed` | Processing error — see `error_message` on status/detail |

## Error responses

All errors return a consistent JSON shape:

```json
{"detail": "Human-readable message", "error_code": "NOT_FOUND"}
```

Validation errors (`422`) also include an `errors` array with field-level details.

## Supported file types

- PDF (`.pdf`, `application/pdf`)
- Word (`.docx`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`)

Interactive docs: **/docs** · OpenAPI schema: **/openapi.json**
"""

OPENAPI_TAGS = [
    {
        "name": "documents",
        "description": "Upload, list, and inspect documents. Processing runs asynchronously via Celery.",
    },
    {
        "name": "chat",
        "description": "RAG-powered Q&A over one or more ready documents, with source citations.",
    },
    {
        "name": "metrics",
        "description": "Operational metrics: document counts, processing stats, and system performance.",
    },
    {
        "name": "health",
        "description": "Liveness checks for API, database, Redis, and Celery worker.",
    },
    {
        "name": "root",
        "description": "API entry point and documentation links.",
    },
]
