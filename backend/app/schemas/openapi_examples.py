EXAMPLE_DOC_ID = "550e8400-e29b-41d4-a716-446655440000"
EXAMPLE_DOC_ID_2 = "6ba7b812-9dad-11d1-80b4-00c04fd430c8"
EXAMPLE_SESSION_ID = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
EXAMPLE_MESSAGE_ID = "6ba7b811-9dad-11d1-80b4-00c04fd430c8"
EXAMPLE_CHUNK_ID = "7c9e6679-7425-40de-944b-e07fc1f90ae7"

ERROR_NOT_FOUND_EXAMPLE = {"detail": "Document not found.", "error_code": "NOT_FOUND"}
ERROR_BAD_REQUEST_EXAMPLE = {
    "detail": "Unsupported file type. Upload a PDF or DOCX file.",
    "error_code": "BAD_REQUEST",
}
ERROR_CONFLICT_EXAMPLE = {
    "detail": "Document is not ready yet.",
    "error_code": "CONFLICT",
}
ERROR_VALIDATION_EXAMPLE = {
    "detail": "Request validation failed.",
    "error_code": "VALIDATION_ERROR",
    "errors": [
        {
            "type": "string_too_short",
            "loc": ["body", "question"],
            "msg": "String should have at least 1 character",
            "input": "",
        }
    ],
}
ERROR_RATE_LIMIT_EXAMPLE = {
    "detail": "Upload rate limit exceeded. Try again later.",
    "error_code": "RATE_LIMIT_EXCEEDED",
}
ERROR_BAD_GATEWAY_EXAMPLE = {
    "detail": "Failed to generate answer. Please try again.",
    "error_code": "HTTP_ERROR",
}

DOCUMENT_UPLOAD_EXAMPLE = {
    "id": EXAMPLE_DOC_ID,
    "filename": "contract.pdf",
    "status": "pending",
    "message": "Document queued for processing",
}

DOCUMENT_UPLOAD_BATCH_EXAMPLE = {
    "accepted": [DOCUMENT_UPLOAD_EXAMPLE],
    "failed": [{"filename": "notes.txt", "error": "Unsupported file type. Upload a PDF or DOCX file."}],
    "queued_count": 1,
    "failed_count": 1,
    "message": "1 document(s) queued for processing. 1 file(s) failed validation.",
}

DOCUMENT_LIST_EXAMPLE = {
    "items": [
        {
            "id": EXAMPLE_DOC_ID,
            "filename": "contract.pdf",
            "status": "ready",
            "file_size_bytes": 245760,
            "page_count": 12,
            "chunk_count": 34,
            "created_at": "2026-06-23T12:00:00Z",
        }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20,
}

DOCUMENT_DETAIL_EXAMPLE = {
    **DOCUMENT_LIST_EXAMPLE["items"][0],
    "content_type": "application/pdf",
    "summary": "A service contract with monthly billing and a December 2025 renewal date.",
    "insights": ["Renewal date is December 2025", "Billing cycle is monthly"],
    "error_message": None,
    "processing_started_at": "2026-06-23T12:00:01Z",
    "processing_completed_at": "2026-06-23T12:00:45Z",
    "updated_at": "2026-06-23T12:00:45Z",
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
    "category": "Contract",
    "tags": ["renewal", "billing", "service agreement"],
    "sentiment": "neutral",
}

CHAT_MESSAGE_EXAMPLE = {
    "id": EXAMPLE_MESSAGE_ID,
    "role": "assistant",
    "content": "The contract renewal date is December 2025.",
    "citations": [
        {
            "chunk_id": EXAMPLE_CHUNK_ID,
            "document_id": EXAMPLE_DOC_ID,
            "document_filename": "contract.pdf",
            "page_number": 1,
            "excerpt": "Renewal date: December 2025.",
            "score": 0.91,
            "source_index": 1,
        }
    ],
    "created_at": "2026-06-23T12:05:00Z",
}

CHAT_MESSAGE_REQUEST_EXAMPLE = {"question": "When is the renewal date?"}

CHAT_SESSION_CREATE_EXAMPLE = {
    "id": EXAMPLE_SESSION_ID,
    "document_id": EXAMPLE_DOC_ID,
    "document_ids": [EXAMPLE_DOC_ID],
    "title": "Chat with contract.pdf",
    "created_at": "2026-06-23T12:05:00Z",
}

MULTI_CHAT_SESSION_REQUEST_EXAMPLE = {
    "document_ids": [EXAMPLE_DOC_ID, EXAMPLE_DOC_ID_2],
    "title": "Compare policies",
}

CHAT_SESSION_DETAIL_EXAMPLE = {
    **CHAT_SESSION_CREATE_EXAMPLE,
    "updated_at": "2026-06-23T12:10:00Z",
    "message_count": 4,
}

CHAT_HISTORY_EXAMPLE = {
    "session_id": EXAMPLE_SESSION_ID,
    "document_id": EXAMPLE_DOC_ID,
    "document_ids": [EXAMPLE_DOC_ID],
    "title": "Policy Renewal Date",
    "messages": [CHAT_MESSAGE_EXAMPLE],
}

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

STORAGE_METRICS_EXAMPLE = {
    "total_file_bytes": 5242880,
    "filesystem_bytes": 5242880,
    "total_chunks": 340,
    "total_chat_sessions": 12,
    "total_chat_messages": 86,
    "embedding_dimension": 384,
}

PROCESSING_HISTORY_EXAMPLE = {
    "items": [
        {
            "id": EXAMPLE_DOC_ID,
            "document_id": EXAMPLE_DOC_ID,
            "stage": "embed",
            "status": "completed",
            "duration_ms": 1200,
            "error_message": None,
            "created_at": "2026-06-23T12:01:00Z",
        }
    ],
    "total": 48,
    "limit": 50,
    "offset": 0,
}

HEALTH_EXAMPLE = {
    "service": "document-vault-ai",
    "api": "ok",
    "database": "ok",
    "redis": "ok",
    "worker": "ok",
    "status": "ok",
}

SYSTEM_METRICS_EXAMPLE = {
    "avg_api_latency_ms": 42.5,
    "p95_api_latency_ms": 118.0,
    "api_request_samples": 128,
    "api_latency_by_route": [
        {
            "route": "GET /api/v1/documents/{id}/status",
            "avg_duration_ms": 18.2,
            "p95_duration_ms": 45.0,
            "sample_count": 64,
        },
        {
            "route": "POST /api/v1/chat/sessions/{id}/messages",
            "avg_duration_ms": 920.5,
            "p95_duration_ms": 1450.0,
            "sample_count": 22,
        },
    ],
    "worker_queue_depth": 2,
    "documents_per_hour": 5,
    "document_failure_rate": 0.0833,
    "processing_failure_rate": 0.0625,
    "avg_processing_duration_ms": 820.5,
    "stage_avg_duration_ms": [
        {"stage": "extract", "completed": 10, "failed": 0, "avg_duration_ms": 450.0},
        {"stage": "embed", "completed": 10, "failed": 0, "avg_duration_ms": 1200.0},
    ],
    "chat": {
        "total_requests": 48,
        "error_count": 2,
        "error_rate": 0.0417,
        "avg_rag_duration_ms": 890.0,
        "avg_retrieval_duration_ms": 120.5,
    },
}

CHAT_STREAM_SSE_EXAMPLE = (
    'data: {"token": "The"}\n\n'
    'data: {"token": " renewal"}\n\n'
    'data: {"done": true}\n\n'
)
