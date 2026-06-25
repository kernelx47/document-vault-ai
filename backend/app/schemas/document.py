from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DocumentStatus
from app.schemas.openapi_examples import (
    DOCUMENT_INSIGHTS_EXAMPLE,
    DOCUMENT_STATUS_EXAMPLE,
    DOCUMENT_UPLOAD_EXAMPLE,
)


class DocumentUploadResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [DOCUMENT_UPLOAD_EXAMPLE]})

    id: UUID
    filename: str
    status: DocumentStatus
    message: str = "Document queued for processing"


class DocumentUploadBatchFailure(BaseModel):
    filename: str
    error: str


class DocumentUploadBatchResponse(BaseModel):
    accepted: list[DocumentUploadResponse]
    failed: list[DocumentUploadBatchFailure]
    queued_count: int
    failed_count: int
    message: str


class DocumentStatusResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [DOCUMENT_STATUS_EXAMPLE]})

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
    model_config = ConfigDict(json_schema_extra={"examples": [DOCUMENT_INSIGHTS_EXAMPLE]})

    id: UUID
    status: DocumentStatus
    summary: str | None = None
    insights: list[str] = Field(default_factory=list)


class DocumentListResponse(BaseModel):
    items: list[DocumentSummary]
    total: int
    page: int
    page_size: int
