from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document, DocumentStatus, ProcessingJob, ProcessingJobStatus
from app.schemas.metrics import DocumentMetricsResponse, ProcessingMetricsResponse, StageMetrics


async def get_document_metrics(db: AsyncSession) -> DocumentMetricsResponse:
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
