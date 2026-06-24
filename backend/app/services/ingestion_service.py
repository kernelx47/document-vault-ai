import time
import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.ai.chunking import chunk_segments
from app.ai.embeddings import get_embedding_provider
from app.ai.extractors import extract_text
from app.ai.llm import generate_summary_and_insights
from app.db.sync_session import SessionLocal
from app.models import Document, DocumentChunk, DocumentStatus, ProcessingJob, ProcessingJobStatus


def process_document(document_id: uuid.UUID) -> None:
    session = SessionLocal()
    try:
        document = session.get(Document, document_id)
        if document is None:
            return

        document.status = DocumentStatus.PROCESSING
        document.processing_started_at = datetime.now(UTC)
        document.error_message = None
        session.commit()

        _run_stage(session, document, "extract", lambda: _extract_stage(session, document))
        _run_stage(session, document, "chunk", lambda: _chunk_stage(session, document))
        _run_stage(session, document, "embed", lambda: _embed_stage(session, document))
        _run_stage(session, document, "summarize", lambda: _summarize_stage(session, document))
        _run_stage(session, document, "complete", lambda: _complete_stage(session, document))
    except Exception as exc:
        session.rollback()
        document = session.get(Document, document_id)
        if document is not None:
            document.status = DocumentStatus.FAILED
            document.error_message = str(exc)
            session.add(
                ProcessingJob(
                    document_id=document.id,
                    status=ProcessingJobStatus.FAILED,
                    stage="failed",
                    error_message=str(exc),
                )
            )
            session.commit()
    finally:
        session.close()


def _run_stage(session: Session, document: Document, stage: str, fn) -> None:
    started = time.perf_counter()
    _record_job(session, document.id, stage, ProcessingJobStatus.STARTED)
    fn()
    duration_ms = int((time.perf_counter() - started) * 1000)
    _record_job(
        session,
        document.id,
        stage,
        ProcessingJobStatus.COMPLETED,
        duration_ms=duration_ms,
    )


def _record_job(
    session: Session,
    document_id: uuid.UUID,
    stage: str,
    status: ProcessingJobStatus,
    duration_ms: int | None = None,
    error_message: str | None = None,
) -> None:
    session.add(
        ProcessingJob(
            document_id=document_id,
            status=status,
            stage=stage,
            duration_ms=duration_ms,
            error_message=error_message,
        )
    )
    session.commit()


def _extract_stage(session: Session, document: Document) -> None:
    segments, page_count = extract_text(document.file_path, document.content_type)
    if not segments:
        raise ValueError("No text could be extracted from the document")
    document.page_count = page_count
    session.commit()
    document._extracted_segments = segments  # type: ignore[attr-defined]


def _chunk_stage(session: Session, document: Document) -> None:
    segments = getattr(document, "_extracted_segments", None)
    if segments is None:
        segments, _ = extract_text(document.file_path, document.content_type)
    chunks = chunk_segments(segments)
    if not chunks:
        raise ValueError("Document produced no chunks after processing")
    document._pending_chunks = chunks  # type: ignore[attr-defined]
    session.commit()


def _embed_stage(session: Session, document: Document) -> None:
    chunks = getattr(document, "_pending_chunks", None)
    if chunks is None:
        raise ValueError("Chunk stage did not run before embed stage")

    provider = get_embedding_provider()
    embeddings = provider.embed_texts([chunk.content for chunk in chunks])

    session.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).delete()
    for chunk, embedding in zip(chunks, embeddings, strict=True):
        session.add(
            DocumentChunk(
                document_id=document.id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                page_number=chunk.page_number,
                token_count=len(chunk.content.split()),
                embedding=embedding,
            )
        )
    document.chunk_count = len(chunks)
    session.commit()


def _summarize_stage(session: Session, document: Document) -> None:
    chunks = (
        session.query(DocumentChunk)
        .filter(DocumentChunk.document_id == document.id)
        .order_by(DocumentChunk.chunk_index)
        .all()
    )
    combined_text = "\n".join(chunk.content for chunk in chunks)
    summary, insights = generate_summary_and_insights(combined_text)
    document.summary = summary
    document.insights = insights
    session.commit()


def _complete_stage(session: Session, document: Document) -> None:
    document.status = DocumentStatus.READY
    document.processing_completed_at = datetime.now(UTC)
    session.commit()
