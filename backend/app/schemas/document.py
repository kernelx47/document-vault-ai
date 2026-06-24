from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DocumentStatus


class DocumentUploadResponse(BaseModel):
    id: UUID
    filename: str
    status: DocumentStatus
    message: str = "Document queued for processing"


class DocumentStatusResponse(BaseModel):
    id: UUID
    status: DocumentStatus
    error_message: str | None = None
    processing_started_at: datetime | None = None
    processing_completed_at: datetime | None = None


class DocumentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    status: DocumentStatus
    file_size_bytes: int
    page_count: int | None = None
    chunk_count: int = 0
    created_at: datetime


class DocumentDetail(DocumentSummary):
    model_config = ConfigDict(from_attributes=True)

    content_type: str
    summary: str | None = None
    insights: list[str] | None = None
    error_message: str | None = None
    processing_started_at: datetime | None = None
    processing_completed_at: datetime | None = None
    updated_at: datetime


class DocumentInsightsResponse(BaseModel):
    id: UUID
    status: DocumentStatus
    summary: str | None = None
    insights: list[str] = Field(default_factory=list)


class DocumentListResponse(BaseModel):
    items: list[DocumentSummary]
    total: int
    page: int
    page_size: int
