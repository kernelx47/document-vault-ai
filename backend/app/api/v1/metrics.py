from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.metrics import DocumentMetricsResponse, ProcessingMetricsResponse
from app.services import metrics_service

router = APIRouter()


@router.get("/documents", response_model=DocumentMetricsResponse)
async def document_metrics(db: AsyncSession = Depends(get_db)) -> DocumentMetricsResponse:
    return await metrics_service.get_document_metrics(db)


@router.get("/processing", response_model=ProcessingMetricsResponse)
async def processing_metrics(db: AsyncSession = Depends(get_db)) -> ProcessingMetricsResponse:
    return await metrics_service.get_processing_metrics(db)
