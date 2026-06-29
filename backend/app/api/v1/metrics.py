"""Operational metrics endpoints: documents, processing, storage, AI usage, and time series."""

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.metrics import (
    AIUsageMetricsResponse,
    DocumentMetricsResponse,
    MetricsTimeseriesResponse,
    ProcessingHistoryResponse,
    ProcessingMetricsResponse,
    StorageMetricsResponse,
    SystemMetricsResponse,
)
from app.services import metrics_service
from app.services.ai_usage_service import get_ai_usage_metrics

router = APIRouter()
logger = logging.getLogger("app.api.metrics")


@router.get(
    "/documents",
    response_model=DocumentMetricsResponse,
    summary="Document metrics",
    response_description="Aggregated document counts and storage totals.",
    description=(
        "Aggregated document counts by processing status, plus total storage and chunk counts. "
        "Useful for dashboards and capacity monitoring."
    ),
)
async def document_metrics(db: AsyncSession = Depends(get_db)) -> DocumentMetricsResponse:
    return await metrics_service.get_document_metrics(db)


@router.get(
    "/processing",
    response_model=ProcessingMetricsResponse,
    summary="Processing metrics",
    response_description="Job counts, failure rate, and per-stage timing.",
    description=(
        "Aggregated processing job stats including failure rate and per-stage breakdown "
        "(extract, chunk, embed, summarize)."
    ),
)
async def processing_metrics(db: AsyncSession = Depends(get_db)) -> ProcessingMetricsResponse:
    return await metrics_service.get_processing_metrics(db)


@router.get(
    "/processing/history",
    response_model=ProcessingHistoryResponse,
    summary="Processing job history",
    response_description="Paginated list of processing job records.",
    description=(
        "Recent processing job records with stage, status, duration, and errors. "
        "Use for debugging failed ingestions and auditing pipeline runs."
    ),
)
async def processing_history(
    limit: int = Query(default=50, ge=1, le=200, description="Maximum records to return."),
    offset: int = Query(default=0, ge=0, description="Pagination offset."),
    db: AsyncSession = Depends(get_db),
) -> ProcessingHistoryResponse:
    return await metrics_service.get_processing_history(db, limit=limit, offset=offset)


@router.get(
    "/storage",
    response_model=StorageMetricsResponse,
    summary="Data storage metrics",
    response_description="File, chunk, and chat storage totals.",
    description=(
        "Storage footprint across uploaded files, indexed chunks, and chat data. "
        "Includes filesystem usage when the upload directory is accessible."
    ),
)
async def storage_metrics(db: AsyncSession = Depends(get_db)) -> StorageMetricsResponse:
    return await metrics_service.get_storage_metrics(db)


@router.get(
    "/system",
    response_model=SystemMetricsResponse,
    summary="System performance metrics",
    response_description="API latency, queue depth, throughput, and failure rates.",
    description=(
        "Operational performance snapshot: API latency (avg and p95), per-route breakdown, "
        "worker queue depth, documents processed per hour, failure rates, and chat/RAG metrics."
    ),
)
async def system_metrics(db: AsyncSession = Depends(get_db)) -> SystemMetricsResponse:
    return await metrics_service.get_system_metrics(db)


@router.get(
    "/ai-usage",
    response_model=AIUsageMetricsResponse,
    summary="AI API usage and cost metrics",
    response_description="Token usage, estimated cost, and daily quota status.",
    description=(
        "Rolling AI usage snapshot: token counts, estimated API cost by operation and provider, "
        "and daily request quota consumption."
    ),
)
async def ai_usage_metrics() -> AIUsageMetricsResponse:
    data = await get_ai_usage_metrics()
    return AIUsageMetricsResponse(**data)


@router.get(
    "/timeseries",
    response_model=MetricsTimeseriesResponse,
    summary="Metrics time series",
    response_description="Hourly AI usage, recent API latency samples, and processing job buckets.",
    description=(
        "Time-bucketed metrics for dashboard sparklines and trend charts. "
        "AI usage is grouped by hour; API latency returns the most recent samples oldest-first."
    ),
)
async def metrics_timeseries(
    hours: int = Query(default=24, ge=1, le=168, description="Lookback window in hours."),
    db: AsyncSession = Depends(get_db),
) -> MetricsTimeseriesResponse:
    return await metrics_service.get_metrics_timeseries(db, hours=hours)
