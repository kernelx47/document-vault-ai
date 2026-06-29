from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.chat import ChatSessionCreateResponse
from app.schemas.document import (
    DocumentDetail,
    DocumentInsightsResponse,
    DocumentListResponse,
    DocumentStatusResponse,
    DocumentUploadBatchResponse,
    DocumentUploadResponse,
)
from app.schemas.openapi_responses import (
    CHAT_SESSION_RESPONSES,
    DOCUMENT_INSIGHTS_RESPONSES,
    DOCUMENT_READ_RESPONSES,
    UPLOAD_RESPONSES,
    merge_responses,
)
from app.services import chat_service, document_service
from app.services.rate_limit_service import enforce_upload_rate_limit

router = APIRouter()


@router.post(
    "/upload",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=DocumentUploadResponse,
    summary="Upload a document",
    response_description="Document accepted and queued for background processing.",
    description=(
        "Upload a single PDF or DOCX file. Returns immediately with `status: pending` "
        "while extraction, chunking, and embedding run asynchronously. "
        "Poll `GET /documents/{id}/status` until `ready`."
    ),
    responses=UPLOAD_RESPONSES,
)
async def upload_document(
    request: Request,
    file: UploadFile = File(..., description="PDF or DOCX file to ingest."),
    db: AsyncSession = Depends(get_db),
) -> DocumentUploadResponse:
    client_ip = request.client.host if request.client else "unknown"
    await enforce_upload_rate_limit(client_ip)
    return await document_service.create_document_upload(db, file)


@router.post(
    "/upload/batch",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=DocumentUploadBatchResponse,
    summary="Upload multiple documents",
    response_description="Batch result with accepted and failed files.",
    description=(
        "Upload multiple PDF or DOCX files in one request. Valid files are queued individually; "
        "invalid files are returned in `failed` without blocking the rest. "
        "Returns `400` only when every file fails validation."
    ),
    responses=UPLOAD_RESPONSES,
)
async def upload_documents_batch(
    request: Request,
    files: list[UploadFile] = File(..., description="One or more PDF/DOCX files."),
    db: AsyncSession = Depends(get_db),
) -> DocumentUploadBatchResponse:
    client_ip = request.client.host if request.client else "unknown"
    await enforce_upload_rate_limit(client_ip)
    return await document_service.create_document_uploads_batch(db, files)


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List documents",
    response_description="Paginated list of documents, newest first.",
    description="Returns document metadata and processing status. Use pagination for large vaults.",
)
async def list_documents(
    page: int = Query(default=1, ge=1, description="Page number (1-based)."),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page (max 100)."),
    db: AsyncSession = Depends(get_db),
) -> DocumentListResponse:
    return await document_service.list_documents(db, page=page, page_size=page_size)


@router.get(
    "/{document_id}",
    response_model=DocumentDetail,
    summary="Get document details",
    response_description="Full document metadata including summary and insights when ready.",
    description="Returns complete document metadata. Insights fields are populated after processing completes.",
    responses=DOCUMENT_READ_RESPONSES,
)
async def get_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> DocumentDetail:
    return await document_service.get_document(db, document_id)


@router.get(
    "/{document_id}/status",
    response_model=DocumentStatusResponse,
    summary="Get processing status",
    response_description="Lightweight status check for polling during ingestion.",
    description=(
        "Poll this endpoint after upload until `status` is `ready` or `failed`. "
        "Lighter than the full detail endpoint — ideal for progress UIs and scripts."
    ),
    responses=DOCUMENT_READ_RESPONSES,
)
async def get_document_status(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> DocumentStatusResponse:
    return await document_service.get_document_status(db, document_id)


@router.get(
    "/{document_id}/insights",
    response_model=DocumentInsightsResponse,
    summary="Get document insights",
    response_description="AI-generated summary and bullet insights.",
    description=(
        "Return AI-generated summary and bullet insights. "
        "Document must be in `ready` status — returns `409` otherwise."
    ),
    responses=DOCUMENT_INSIGHTS_RESPONSES,
)
async def get_document_insights(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> DocumentInsightsResponse:
    return await document_service.get_document_insights(db, document_id)


@router.post(
    "/{document_id}/chat/sessions",
    status_code=status.HTTP_201_CREATED,
    response_model=ChatSessionCreateResponse,
    summary="Start a single-document chat session",
    response_description="New chat session scoped to one ready document.",
    description=(
        "Create a chat session for a processed document. "
        "Use the returned session ID with `POST /chat/sessions/{id}/messages`. "
        "For multi-document chat, use `POST /chat/sessions` instead."
    ),
    responses=merge_responses(DOCUMENT_READ_RESPONSES, CHAT_SESSION_RESPONSES),
)
async def create_document_chat_session(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ChatSessionCreateResponse:
    return await chat_service.create_chat_session(db, document_id)
