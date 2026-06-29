"""Document CRUD operations — upload, list, detail, status, insights, and versioning."""

import logging
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import Document, DocumentStatus, UploadBatch
from app.schemas.batch import BatchDetail, BatchDocumentSummary, BatchListResponse, BatchSummary
from app.schemas.document import (
    DocumentDetail,
    DocumentInsightsResponse,
    DocumentListResponse,
    DocumentStatusResponse,
    DocumentSummary,
    DocumentUploadBatchFailure,
    DocumentUploadBatchResponse,
    DocumentUploadResponse,
    DocumentVersionListResponse,
)
from app.schemas.document_analysis import InsightsRegenerateRequest
from app.ai.llm import regenerate_custom_summary
from app.workers.tasks import process_document_task

logger = logging.getLogger("app.documents")

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
ALLOWED_EXTENSIONS = {".pdf", ".docx"}


class UploadValidationError(Exception):
    """Raised when an uploaded file fails validation checks."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


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
        document_group_id=document_id,
        version_number=1,
        is_latest=True,
    )


def _cleanup_file(document: Document) -> None:
    try:
        path = Path(document.file_path)
        if path.exists():
            path.unlink()
    except OSError:
        logger.warning("Failed to clean up orphan file: %s", document.file_path)


async def _queue_document(db: AsyncSession, document: Document) -> DocumentUploadResponse:
    db.add(document)
    try:
        await db.commit()
        await db.refresh(document)
    except Exception:
        _cleanup_file(document)
        raise

    try:
        process_document_task.delay(str(document.id))
    except Exception:
        logger.exception("Failed to enqueue document %s — will remain in pending state", document.id)

    return DocumentUploadResponse(
        id=document.id,
        filename=document.filename,
        status=document.status,
    )


async def create_document_upload(db: AsyncSession, file: UploadFile) -> DocumentUploadResponse:
    """Validate, store, and queue a single uploaded document for processing."""
    try:
        content = await file.read()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to read uploaded file.") from exc

    try:
        safe_name, content_type = _validate_upload(file, content)
        document = _build_document_record(safe_name, content_type, content)
    except UploadValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc

    return await _queue_document(db, document)


async def create_document_uploads_batch(
    db: AsyncSession, files: list[UploadFile]
) -> DocumentUploadBatchResponse:
    """Validate and queue multiple uploaded documents, collecting per-file failures."""
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
            logger.exception("Batch upload failed for file: %s", filename)
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

    batch = UploadBatch(
        label=f"Batch — {queued_count} file{'s' if queued_count != 1 else ''}",
        total_files=queued_count,
    )
    db.add(batch)
    await db.flush()

    for resp in accepted:
        await db.execute(
            sa_update(Document).where(Document.id == resp.id).values(batch_id=batch.id)
        )
    await db.commit()

    message = f"{queued_count} document(s) queued for processing."
    if failed:
        message += f" {len(failed)} file(s) failed validation."

    return DocumentUploadBatchResponse(
        batch_id=batch.id,
        accepted=accepted,
        failed=failed,
        queued_count=queued_count,
        failed_count=len(failed),
        message=message,
    )


async def list_documents(
    db: AsyncSession, page: int = 1, page_size: int = 20, status_filter: str | None = None
) -> DocumentListResponse:
    """Return a paginated list of documents, newest first, with optional status filter."""
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    offset = (page - 1) * page_size

    base = select(Document)
    count_base = select(func.count()).select_from(Document)
    if status_filter:
        base = base.where(Document.status == status_filter)
        count_base = count_base.where(Document.status == status_filter)

    total = await db.scalar(count_base)
    result = await db.execute(
        base.order_by(Document.created_at.desc()).offset(offset).limit(page_size)
    )
    documents = result.scalars().all()

    return DocumentListResponse(
        items=[DocumentSummary.model_validate(doc) for doc in documents],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


async def get_document(db: AsyncSession, document_id: uuid.UUID) -> DocumentDetail:
    """Return full document metadata by ID."""
    document = await _get_document_or_raise(db, document_id)
    return DocumentDetail.model_validate(document)


async def get_document_status(db: AsyncSession, document_id: uuid.UUID) -> DocumentStatusResponse:
    """Return lightweight processing status for a document."""
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
    """Return AI-generated summary and insights for a ready document."""
    document = await _get_document_or_raise(db, document_id)
    if document.status != DocumentStatus.READY:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document is not ready yet.",
        )
    return _insights_from_document(document)


def _insights_from_document(document: Document) -> DocumentInsightsResponse:
    return DocumentInsightsResponse(
        id=document.id,
        status=document.status,
        summary=document.summary,
        insights=document.insights or [],
        category=document.category,
        tags=[str(tag) for tag in (document.tags or [])],
        sentiment=document.sentiment,
    )


async def regenerate_document_insights(
    db: AsyncSession,
    document_id: uuid.UUID,
    options: InsightsRegenerateRequest,
) -> DocumentInsightsResponse:
    """Re-generate summary and insights with custom length, tone, and focus."""
    from app.models import DocumentChunk

    document = await _get_document_or_raise(db, document_id)
    if document.status != DocumentStatus.READY:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document is not ready yet.",
        )

    result = await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document.id)
        .order_by(DocumentChunk.chunk_index)
    )
    chunks = result.scalars().all()
    combined_text = "\n".join(chunk.content for chunk in chunks)
    summary, insights = regenerate_custom_summary(
        combined_text,
        length=options.length,
        tone=options.tone,
        focus_areas=options.focus_areas,
    )
    document.summary = summary
    document.insights = insights
    await db.commit()
    await db.refresh(document)
    return _insights_from_document(document)


async def _get_document_or_raise(db: AsyncSession, document_id: uuid.UUID) -> Document:
    document = await db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    return document


async def create_document_version(
    db: AsyncSession, document_id: uuid.UUID, file: UploadFile
) -> DocumentUploadResponse:
    """Upload a new version of an existing document into its version group."""
    existing = await _get_document_or_raise(db, document_id)
    try:
        content = await file.read()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to read uploaded file.") from exc

    try:
        safe_name, content_type = _validate_upload(file, content)
        document = _build_document_record(safe_name, content_type, content)
    except UploadValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc

    group_id = existing.document_group_id or existing.id
    latest_version = await db.scalar(
        select(func.max(Document.version_number)).where(Document.document_group_id == group_id)
    )
    document.document_group_id = group_id
    document.version_number = int(latest_version or existing.version_number) + 1
    document.is_latest = True

    result = await db.execute(
        select(Document).where(Document.document_group_id == group_id, Document.is_latest.is_(True))
    )
    for prior in result.scalars().all():
        prior.is_latest = False
        db.add(prior)

    return await _queue_document(db, document)


async def list_document_versions(db: AsyncSession, document_id: uuid.UUID) -> DocumentVersionListResponse:
    """Return all versions of a document group, newest first."""
    from app.schemas.document import DocumentVersionSummary

    document = await _get_document_or_raise(db, document_id)
    group_id = document.document_group_id or document.id
    result = await db.execute(
        select(Document)
        .where(Document.document_group_id == group_id)
        .order_by(Document.version_number.desc())
    )
    versions = result.scalars().all()
    return DocumentVersionListResponse(
        document_group_id=group_id,
        items=[
            DocumentVersionSummary(
                id=item.id,
                filename=item.filename,
                version_number=item.version_number,
                is_latest=item.is_latest,
                status=item.status,
                created_at=item.created_at,
            )
            for item in versions
        ],
        total=len(versions),
    )


async def list_batches(db: AsyncSession, page: int = 1, page_size: int = 20) -> BatchListResponse:
    """Return paginated upload batches with aggregated document status counts."""
    total = await db.scalar(select(func.count()).select_from(UploadBatch)) or 0
    offset = (page - 1) * page_size

    result = await db.execute(
        select(UploadBatch).order_by(UploadBatch.created_at.desc()).limit(page_size).offset(offset)
    )
    batches = result.scalars().all()

    items: list[BatchSummary] = []
    for batch in batches:
        counts = await _batch_status_counts(db, batch.id)
        items.append(BatchSummary(
            id=batch.id,
            label=batch.label,
            total_files=batch.total_files,
            created_at=batch.created_at,
            **counts,
        ))

    return BatchListResponse(items=items, total=int(total), page=page, page_size=page_size)


async def get_batch(db: AsyncSession, batch_id: uuid.UUID) -> BatchDetail:
    """Return a single batch with per-document status breakdown."""
    batch = await db.get(UploadBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found.")

    counts = await _batch_status_counts(db, batch_id)

    docs_result = await db.execute(
        select(Document)
        .where(Document.batch_id == batch_id)
        .order_by(Document.created_at.asc())
    )
    docs = [
        BatchDocumentSummary.model_validate(doc)
        for doc in docs_result.scalars().all()
    ]

    return BatchDetail(
        id=batch.id,
        label=batch.label,
        total_files=batch.total_files,
        created_at=batch.created_at,
        documents=docs,
        **counts,
    )


async def _batch_status_counts(db: AsyncSession, batch_id: uuid.UUID) -> dict[str, int]:
    result = await db.execute(
        select(Document.status, func.count())
        .where(Document.batch_id == batch_id)
        .group_by(Document.status)
    )
    counts = {s.value: c for s, c in result.all()}
    return {
        "ready": counts.get("ready", 0),
        "processing": counts.get("processing", 0),
        "pending": counts.get("pending", 0),
        "failed": counts.get("failed", 0),
    }
