"""Aggregated metrics queries for documents, processing, storage, and system health."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import ChatMessage, ChatSession, Document, DocumentStatus, ProcessingJob, ProcessingJobStatus
from app.schemas.metrics import (
    ChatMetrics,
    DocumentMetricsResponse,
    MetricsTimeseriesResponse,
    ProcessingHistoryResponse,
    ProcessingJobRecord,
    ProcessingMetricsResponse,
    ProcessingTimeSeriesPoint,
    StageMetrics,
    StorageMetricsResponse,
    SystemMetricsResponse,
    AIUsageTimeSeriesPoint,
)
from app.services.api_latency import get_api_latency_stats, get_recent_api_latency_samples
from app.services.ai_usage_service import get_ai_usage_timeseries
from app.services.rag_metrics import get_chat_metrics
from app.services.worker_health import get_worker_queue_depth


async def get_document_metrics(db: AsyncSession) -> DocumentMetricsResponse:
    """Return aggregated document counts by status and storage totals."""
    status_result = await db.execute(
        select(Document.status, func.count()).group_by(Document.status)
    )
    counts = {status.value: count for status, count in status_result.all()}

    total_size = await db.scalar(
        select(func.coalesce(func.sum(Document.file_size_bytes), 0))
    )
    total_chunks = await db.scalar(select(func.coalesce(func.sum(Document.chunk_count), 0)))

    return DocumentMetricsResponse(
        total=sum(counts.values()),
        pending=counts.get(DocumentStatus.PENDING.value, 0),
        processing=counts.get(DocumentStatus.PROCESSING.value, 0),
        ready=counts.get(DocumentStatus.READY.value, 0),
        failed=counts.get(DocumentStatus.FAILED.value, 0),
        total_size_bytes=int(total_size or 0),
        total_chunks=int(total_chunks or 0),
    )


async def get_processing_metrics(db: AsyncSession) -> ProcessingMetricsResponse:
    """Return processing job counts, failure rate, and per-stage timing."""
    status_result = await db.execute(
        select(ProcessingJob.status, func.count()).group_by(ProcessingJob.status)
    )
    status_counts = {status.value: count for status, count in status_result.all()}
    total_jobs = sum(status_counts.values())

    avg_duration = await db.scalar(
        select(func.avg(ProcessingJob.duration_ms)).where(
            ProcessingJob.status == ProcessingJobStatus.COMPLETED,
            ProcessingJob.duration_ms.isnot(None),
        )
    )

    stage_result = await db.execute(
        select(
            ProcessingJob.stage,
            ProcessingJob.status,
            func.count(),
            func.avg(ProcessingJob.duration_ms),
        ).group_by(ProcessingJob.stage, ProcessingJob.status)
    )

    stage_map: dict[str, StageMetrics] = {}
    for stage, job_status, count, stage_avg_duration in stage_result.all():
        if stage not in stage_map:
            stage_map[stage] = StageMetrics(stage=stage)
        entry = stage_map[stage]
        if job_status == ProcessingJobStatus.COMPLETED:
            entry.completed = count
            entry.avg_duration_ms = round(stage_avg_duration, 2) if stage_avg_duration else None
        elif job_status == ProcessingJobStatus.FAILED:
            entry.failed = count

    failed = status_counts.get(ProcessingJobStatus.FAILED.value, 0)
    failure_rate = round(failed / total_jobs, 4) if total_jobs else 0.0

    return ProcessingMetricsResponse(
        total_jobs=total_jobs,
        started=status_counts.get(ProcessingJobStatus.STARTED.value, 0),
        completed=status_counts.get(ProcessingJobStatus.COMPLETED.value, 0),
        failed=failed,
        avg_duration_ms=round(avg_duration, 2) if avg_duration else None,
        failure_rate=failure_rate,
        by_stage=sorted(stage_map.values(), key=lambda item: item.stage),
    )


async def get_storage_metrics(db: AsyncSession) -> StorageMetricsResponse:
    """Return storage footprint across files, chunks, and chat data."""
    settings = get_settings()

    total_file_bytes = await db.scalar(
        select(func.coalesce(func.sum(Document.file_size_bytes), 0))
    )
    total_chunks = await db.scalar(select(func.coalesce(func.sum(Document.chunk_count), 0)))
    total_chat_sessions = await db.scalar(select(func.count()).select_from(ChatSession))
    total_chat_messages = await db.scalar(select(func.count()).select_from(ChatMessage))

    filesystem_bytes: int | None = None
    upload_dir = Path(settings.upload_dir)
    if upload_dir.is_dir():
        filesystem_bytes = sum(
            file.stat().st_size for file in upload_dir.rglob("*") if file.is_file()
        )

    return StorageMetricsResponse(
        total_file_bytes=int(total_file_bytes or 0),
        filesystem_bytes=filesystem_bytes,
        total_chunks=int(total_chunks or 0),
        total_chat_sessions=int(total_chat_sessions or 0),
        total_chat_messages=int(total_chat_messages or 0),
        embedding_dimension=settings.embedding_dimension,
    )


async def get_processing_history(
    db: AsyncSession, *, limit: int = 50, offset: int = 0
) -> ProcessingHistoryResponse:
    """Return paginated processing job records for audit and debugging."""
    total = await db.scalar(select(func.count()).select_from(ProcessingJob)) or 0

    result = await db.execute(
        select(ProcessingJob)
        .order_by(ProcessingJob.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    items = [
        ProcessingJobRecord.model_validate(job)
        for job in result.scalars().all()
    ]

    return ProcessingHistoryResponse(
        items=items,
        total=int(total),
        limit=limit,
        offset=offset,
    )


async def get_system_metrics(db: AsyncSession) -> SystemMetricsResponse:
    """Return an operational performance snapshot: latency, queue depth, and failure rates."""
    avg_api_latency_ms, p95_api_latency_ms, api_request_samples, api_latency_by_route = (
        await get_api_latency_stats()
    )
    worker_queue_depth = await get_worker_queue_depth()
    chat_total, chat_errors, chat_error_rate, avg_rag_ms, avg_retrieval_ms = await get_chat_metrics()

    one_hour_ago = datetime.now(UTC) - timedelta(hours=1)
    documents_processed_last_hour = await db.scalar(
        select(func.count())
        .select_from(Document)
        .where(
            Document.processing_completed_at.isnot(None),
            Document.processing_completed_at >= one_hour_ago,
        )
    )

    status_result = await db.execute(
        select(Document.status, func.count()).group_by(Document.status)
    )
    doc_counts = {status.value: count for status, count in status_result.all()}
    doc_total = sum(doc_counts.values())
    doc_failed = doc_counts.get(DocumentStatus.FAILED.value, 0)
    document_failure_rate = round(doc_failed / doc_total, 4) if doc_total else 0.0

    processing = await get_processing_metrics(db)

    return SystemMetricsResponse(
        avg_api_latency_ms=avg_api_latency_ms,
        p95_api_latency_ms=p95_api_latency_ms,
        api_request_samples=api_request_samples,
        api_latency_by_route=api_latency_by_route,
        worker_queue_depth=worker_queue_depth,
        documents_per_hour=int(documents_processed_last_hour or 0),
        document_failure_rate=document_failure_rate,
        processing_failure_rate=processing.failure_rate,
        avg_processing_duration_ms=processing.avg_duration_ms,
        stage_avg_duration_ms=processing.by_stage,
        chat=ChatMetrics(
            total_requests=chat_total,
            error_count=chat_errors,
            error_rate=chat_error_rate,
            avg_rag_duration_ms=avg_rag_ms,
            avg_retrieval_duration_ms=avg_retrieval_ms,
        ),
    )


async def get_metrics_timeseries(db: AsyncSession, *, hours: int = 24) -> MetricsTimeseriesResponse:
    """Return time-bucketed metrics for dashboard sparklines and trend charts."""
    ai_usage_raw = await get_ai_usage_timeseries(hours=hours)
    ai_usage = [AIUsageTimeSeriesPoint(**point) for point in ai_usage_raw]
    api_latency_ms = await get_recent_api_latency_samples(limit=60)

    cutoff = datetime.now(UTC) - timedelta(hours=hours)
    result = await db.execute(
        select(ProcessingJob.created_at, ProcessingJob.status).where(ProcessingJob.created_at >= cutoff)
    )
    buckets: dict[str, dict[str, int | str]] = {}
    for created_at, status in result.all():
        key = created_at.strftime("%Y-%m-%dT%H:00")
        label = created_at.strftime("%b %d %H:00")
        bucket = buckets.setdefault(key, {"label": label, "completed": 0, "failed": 0})
        if status == ProcessingJobStatus.FAILED:
            bucket["failed"] = int(bucket["failed"]) + 1
        elif status == ProcessingJobStatus.COMPLETED:
            bucket["completed"] = int(bucket["completed"]) + 1

    processing_jobs = [
        ProcessingTimeSeriesPoint(
            label=str(buckets[key]["label"]),
            completed=int(buckets[key]["completed"]),
            failed=int(buckets[key]["failed"]),
        )
        for key in sorted(buckets.keys())
    ]

    return MetricsTimeseriesResponse(
        ai_usage=ai_usage,
        api_latency_ms=api_latency_ms,
        processing_jobs=processing_jobs,
    )
