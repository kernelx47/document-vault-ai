import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.metrics import DocumentMetricsResponse, ProcessingMetricsResponse, SystemMetricsResponse
from app.services import metrics_service

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
    "/system",
    response_model=SystemMetricsResponse,
    summary="System performance metrics",
    response_description="API latency, queue depth, throughput, and failure rates.",
    description=(
        "Operational performance snapshot: API latency, worker queue depth, "
        "documents processed per hour, and failure rates."
    ),
)
async def system_metrics(db: AsyncSession = Depends(get_db)) -> SystemMetricsResponse:
    return await metrics_service.get_system_metrics(db)
