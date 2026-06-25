EXAMPLE_DOC_ID = "550e8400-e29b-41d4-a716-446655440000"
EXAMPLE_SESSION_ID = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
EXAMPLE_MESSAGE_ID = "6ba7b811-9dad-11d1-80b4-00c04fd430c8"
EXAMPLE_CHUNK_ID = "7c9e6679-7425-40de-944b-e07fc1f90ae7"

DOCUMENT_UPLOAD_EXAMPLE = {
    "id": EXAMPLE_DOC_ID,
    "filename": "contract.pdf",
    "status": "pending",
    "message": "Document queued for processing",
}

DOCUMENT_STATUS_EXAMPLE = {
    "id": EXAMPLE_DOC_ID,
    "status": "ready",
    "error_message": None,
    "processing_started_at": "2026-06-23T12:00:01Z",
    "processing_completed_at": "2026-06-23T12:00:45Z",
}

DOCUMENT_INSIGHTS_EXAMPLE = {
    "id": EXAMPLE_DOC_ID,
    "status": "ready",
    "summary": "A service contract with monthly billing and a December 2025 renewal date.",
    "insights": [
        "Renewal date is December 2025",
        "Billing cycle is monthly",
        "Document is a sample contract",
    ],
}

CHAT_MESSAGE_EXAMPLE = {
    "id": EXAMPLE_MESSAGE_ID,
    "role": "assistant",
    "content": "The contract renewal date is December 2025.",
    "citations": [
        {
            "chunk_id": EXAMPLE_CHUNK_ID,
            "page_number": 1,
            "excerpt": "Renewal date: December 2025.",
            "score": 0.91,
        }
    ],
    "created_at": "2026-06-23T12:05:00Z",
}

CHAT_MESSAGE_REQUEST_EXAMPLE = {"question": "When is the renewal date?"}

DOCUMENT_METRICS_EXAMPLE = {
    "total": 12,
    "pending": 1,
    "processing": 0,
    "ready": 10,
    "failed": 1,
    "total_size_bytes": 5242880,
    "total_chunks": 340,
}

PROCESSING_METRICS_EXAMPLE = {
    "total_jobs": 48,
    "started": 0,
    "completed": 45,
    "failed": 3,
    "avg_duration_ms": 820.5,
    "failure_rate": 0.0625,
    "by_stage": [
        {"stage": "embed", "completed": 10, "failed": 0, "avg_duration_ms": 1200.0},
        {"stage": "extract", "completed": 10, "failed": 0, "avg_duration_ms": 450.0},
    ],
}

HEALTH_EXAMPLE = {
    "service": "document-vault-ai",
    "api": "ok",
    "database": "ok",
    "redis": "ok",
    "status": "ok",
}
