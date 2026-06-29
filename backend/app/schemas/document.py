from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DocumentStatus
from app.schemas.openapi_examples import (
    DOCUMENT_DETAIL_EXAMPLE,
    DOCUMENT_INSIGHTS_EXAMPLE,
    DOCUMENT_LIST_EXAMPLE,
    DOCUMENT_STATUS_EXAMPLE,
    DOCUMENT_UPLOAD_BATCH_EXAMPLE,
    DOCUMENT_UPLOAD_EXAMPLE,
)


class DocumentUploadResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [DOCUMENT_UPLOAD_EXAMPLE]})

    id: UUID = Field(description="Unique document identifier. Use for status polling and chat.")
    filename: str = Field(description="Original uploaded filename.")
    status: DocumentStatus = Field(
        description="Processing state: `pending` → `processing` → `ready` or `failed`."
    )
    message: str = Field(
        default="Document queued for processing",
        description="Human-readable confirmation that ingestion was queued.",
    )


class DocumentUploadBatchFailure(BaseModel):
    filename: str = Field(description="Name of the file that failed validation.")
    error: str = Field(description="Reason the file was rejected.")


class DocumentUploadBatchResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [DOCUMENT_UPLOAD_BATCH_EXAMPLE]})

    accepted: list[DocumentUploadResponse] = Field(description="Files queued for processing.")
    failed: list[DocumentUploadBatchFailure] = Field(
        description="Files rejected during validation (invalid type, size, etc.)."
    )
    queued_count: int = Field(description="Number of documents successfully queued.")
    failed_count: int = Field(description="Number of files that failed validation.")
    message: str = Field(description="Summary of batch upload results.")


class DocumentStatusResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [DOCUMENT_STATUS_EXAMPLE]})

    id: UUID
    status: DocumentStatus = Field(description="Current processing state.")
    error_message: str | None = Field(
        default=None, description="Failure reason when status is `failed`; otherwise null."
    )
    processing_started_at: datetime | None = Field(
        default=None, description="When background processing began."
    )
    processing_completed_at: datetime | None = Field(
        default=None, description="When processing finished (ready or failed)."
    )


class DocumentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    status: DocumentStatus
    file_size_bytes: int = Field(description="Uploaded file size in bytes.")
    page_count: int | None = Field(default=None, description="Extracted page count, if available.")
    chunk_count: int = Field(default=0, description="Number of text chunks indexed for RAG.")
    created_at: datetime


class DocumentDetail(DocumentSummary):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={"examples": [DOCUMENT_DETAIL_EXAMPLE]},
    )

    content_type: str = Field(description="MIME type of the uploaded file.")
    summary: str | None = Field(default=None, description="AI-generated document summary.")
    insights: list[str] | None = Field(default=None, description="AI-generated bullet insights.")
    error_message: str | None = None
    processing_started_at: datetime | None = None
    processing_completed_at: datetime | None = None
    updated_at: datetime


class DocumentInsightsResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [DOCUMENT_INSIGHTS_EXAMPLE]})

    id: UUID
    status: DocumentStatus
    summary: str | None = Field(default=None, description="One-paragraph summary of the document.")
    insights: list[str] = Field(default_factory=list, description="Key facts extracted from the document.")


class DocumentListResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [DOCUMENT_LIST_EXAMPLE]})

    items: list[DocumentSummary]
    total: int = Field(description="Total documents matching the query (across all pages).")
    page: int = Field(description="Current page number (1-based).")
    page_size: int = Field(description="Maximum items per page.")
