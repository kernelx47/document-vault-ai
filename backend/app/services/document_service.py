import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import Document, DocumentStatus
from app.schemas.document import (
    DocumentDetail,
    DocumentInsightsResponse,
    DocumentListResponse,
    DocumentStatusResponse,
    DocumentSummary,
    DocumentUploadBatchFailure,
    DocumentUploadBatchResponse,
    DocumentUploadResponse,
)
from app.workers.tasks import process_document_task

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
ALLOWED_EXTENSIONS = {".pdf", ".docx"}


class UploadValidationError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class DocumentNotFoundError(Exception):
    pass


def _validate_upload(file: UploadFile, content: bytes) -> tuple[str, str]:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise UploadValidationError("Unsupported file type. Upload a PDF or DOCX file.")

    extension = Path(file.filename or "").suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise UploadValidationError("Unsupported file extension. Use .pdf or .docx.")

    settings = get_settings()
    max_size = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_size:
        raise UploadValidationError(
            f"File exceeds maximum size of {settings.max_upload_size_mb}MB."
        )
    if not content:
        raise UploadValidationError("Uploaded file is empty.")

    safe_name = Path(file.filename or "upload").name
    return safe_name, file.content_type or "application/octet-stream"


def _build_document_record(safe_name: str, content_type: str, content: bytes) -> Document:
    settings = get_settings()
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    document_id = uuid.uuid4()
    stored_path = upload_dir / f"{document_id}_{safe_name}"
    stored_path.write_bytes(content)

    return Document(
        id=document_id,
        filename=safe_name,
        content_type=content_type,
        file_path=str(stored_path),
        file_size_bytes=len(content),
        status=DocumentStatus.PENDING,
    )


async def _queue_document(db: AsyncSession, document: Document) -> DocumentUploadResponse:
    db.add(document)
    await db.commit()
    await db.refresh(document)
    process_document_task.delay(str(document.id))
    return DocumentUploadResponse(
        id=document.id,
        filename=document.filename,
        status=document.status,
    )


async def create_document_upload(db: AsyncSession, file: UploadFile) -> DocumentUploadResponse:
    content = await file.read()
    try:
        safe_name, content_type = _validate_upload(file, content)
        document = _build_document_record(safe_name, content_type, content)
    except UploadValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc

    return await _queue_document(db, document)


async def create_document_uploads_batch(
    db: AsyncSession, files: list[UploadFile]
) -> DocumentUploadBatchResponse:
    settings = get_settings()

    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No files provided.")
    if len(files) > settings.max_batch_upload_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Maximum {settings.max_batch_upload_files} files per batch. "
                "Split large uploads into multiple batch requests."
            ),
        )

    accepted: list[DocumentUploadResponse] = []
    failed: list[DocumentUploadBatchFailure] = []

    for file in files:
        filename = file.filename or "unknown"
        try:
            content = await file.read()
            safe_name, content_type = _validate_upload(file, content)
            document = _build_document_record(safe_name, content_type, content)
            upload_response = await _queue_document(db, document)
            accepted.append(upload_response)
        except UploadValidationError as exc:
            await db.rollback()
            failed.append(DocumentUploadBatchFailure(filename=filename, error=exc.message))
        except Exception:
            await db.rollback()
            failed.append(
                DocumentUploadBatchFailure(
                    filename=filename,
                    error="Unexpected error while saving file.",
                )
            )

    if not accepted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="All uploads failed.",
            headers={"X-Upload-Failures": str(len(failed))},
        )

    queued_count = len(accepted)
    message = f"{queued_count} document(s) queued for processing."
    if failed:
        message += f" {len(failed)} file(s) failed validation."

    return DocumentUploadBatchResponse(
        accepted=accepted,
        failed=failed,
        queued_count=queued_count,
        failed_count=len(failed),
        message=message,
    )


async def list_documents(db: AsyncSession, page: int = 1, page_size: int = 20) -> DocumentListResponse:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    offset = (page - 1) * page_size

    total = await db.scalar(select(func.count()).select_from(Document))
    result = await db.execute(
        select(Document).order_by(Document.created_at.desc()).offset(offset).limit(page_size)
    )
    documents = result.scalars().all()

    return DocumentListResponse(
        items=[DocumentSummary.model_validate(doc) for doc in documents],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


async def get_document(db: AsyncSession, document_id: uuid.UUID) -> DocumentDetail:
    document = await _get_document_or_raise(db, document_id)
    return DocumentDetail.model_validate(document)


async def get_document_status(db: AsyncSession, document_id: uuid.UUID) -> DocumentStatusResponse:
    document = await _get_document_or_raise(db, document_id)
    return DocumentStatusResponse(
        id=document.id,
        status=document.status,
        error_message=document.error_message,
        processing_started_at=document.processing_started_at,
        processing_completed_at=document.processing_completed_at,
    )


async def get_document_insights(
    db: AsyncSession, document_id: uuid.UUID
) -> DocumentInsightsResponse:
    document = await _get_document_or_raise(db, document_id)
    if document.status != DocumentStatus.READY:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document is not ready yet.",
        )
    return DocumentInsightsResponse(
        id=document.id,
        status=document.status,
        summary=document.summary,
        insights=document.insights or [],
    )


async def _get_document_or_raise(db: AsyncSession, document_id: uuid.UUID) -> Document:
    document = await db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    return document
