from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.services.rate_limit_service import enforce_upload_rate_limit
from app.schemas.chat import ChatSessionCreateResponse
from app.schemas.document import (
    DocumentDetail,
    DocumentInsightsResponse,
    DocumentListResponse,
    DocumentStatusResponse,
    DocumentUploadBatchResponse,
    DocumentUploadResponse,
)
from app.services import chat_service, document_service

router = APIRouter()


@router.post("/upload", status_code=status.HTTP_202_ACCEPTED, response_model=DocumentUploadResponse)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> DocumentUploadResponse:
    client_ip = request.client.host if request.client else "unknown"
    await enforce_upload_rate_limit(client_ip)
    return await document_service.create_document_upload(db, file)


@router.post(
    "/upload/batch",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=DocumentUploadBatchResponse,
)
async def upload_documents_batch(
    request: Request,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
) -> DocumentUploadBatchResponse:
    client_ip = request.client.host if request.client else "unknown"
    await enforce_upload_rate_limit(client_ip)
    return await document_service.create_document_uploads_batch(db, files)


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> DocumentListResponse:
    return await document_service.list_documents(db, page=page, page_size=page_size)


@router.get("/{document_id}", response_model=DocumentDetail)
async def get_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> DocumentDetail:
    return await document_service.get_document(db, document_id)


@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> DocumentStatusResponse:
    return await document_service.get_document_status(db, document_id)


@router.get("/{document_id}/insights", response_model=DocumentInsightsResponse)
async def get_document_insights(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> DocumentInsightsResponse:
    return await document_service.get_document_insights(db, document_id)


@router.post(
    "/{document_id}/chat/sessions",
    status_code=status.HTTP_201_CREATED,
    response_model=ChatSessionCreateResponse,
)
async def create_document_chat_session(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ChatSessionCreateResponse:
    return await chat_service.create_chat_session(db, document_id)
