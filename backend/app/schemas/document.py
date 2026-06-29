"""Pydantic schemas for document upload, status, listing, and versioning endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

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
    """Response confirming a single document upload was accepted for processing."""

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
    """Details of a single file that failed validation during batch upload."""

    filename: str = Field(description="Name of the file that failed validation.")
    error: str = Field(description="Reason the file was rejected.")


class DocumentUploadBatchResponse(BaseModel):
    """Response summarizing the results of a batch document upload."""

    model_config = ConfigDict(json_schema_extra={"examples": [DOCUMENT_UPLOAD_BATCH_EXAMPLE]})

    batch_id: UUID | None = Field(default=None, description="Batch tracking ID for the Activity Monitor.")
    accepted: list[DocumentUploadResponse] = Field(description="Files queued for processing.")
    failed: list[DocumentUploadBatchFailure] = Field(
        description="Files rejected during validation (invalid type, size, etc.)."
    )
    queued_count: int = Field(description="Number of documents successfully queued.")
    failed_count: int = Field(description="Number of files that failed validation.")
    message: str = Field(description="Summary of batch upload results.")


class DocumentStatusResponse(BaseModel):
    """Response for polling a document's current processing status."""

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
    """Compact document representation used in list responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    status: DocumentStatus
    file_size_bytes: int = Field(description="Uploaded file size in bytes.")
    page_count: int | None = Field(default=None, description="Extracted page count, if available.")
    chunk_count: int = Field(default=0, description="Number of text chunks indexed for RAG.")
    category: str | None = Field(default=None, description="AI-assigned document category.")
    tags: list[str] = Field(default_factory=list, description="AI-assigned topical tags.")
    sentiment: str | None = Field(default=None, description="Overall document sentiment.")
    version_number: int = Field(default=1, description="Version within the document group.")
    is_latest: bool = Field(default=True, description="Whether this is the current version.")
    created_at: datetime

    @field_validator("tags", mode="before")
    @classmethod
    def _normalize_tags(cls, value: object) -> list[str]:
        if not value:
            return []
        return [str(item) for item in value]


class DocumentDetail(DocumentSummary):
    """Full document details including AI-generated summary and insights."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={"examples": [DOCUMENT_DETAIL_EXAMPLE]},
    )

    document_group_id: UUID | None = Field(
        default=None, description="Shared ID linking all versions of the same logical document."
    )
    content_type: str = Field(description="MIME type of the uploaded file.")
    summary: str | None = Field(default=None, description="AI-generated document summary.")
    insights: list[str] | None = Field(default=None, description="AI-generated bullet insights.")
    error_message: str | None = None
    processing_started_at: datetime | None = None
    processing_completed_at: datetime | None = None
    updated_at: datetime


class DocumentInsightsResponse(BaseModel):
    """Response containing AI-generated insights for a document."""

    model_config = ConfigDict(json_schema_extra={"examples": [DOCUMENT_INSIGHTS_EXAMPLE]})

    id: UUID
    status: DocumentStatus
    summary: str | None = Field(default=None, description="One-paragraph summary of the document.")
    insights: list[str] = Field(default_factory=list, description="Key facts extracted from the document.")
    category: str | None = Field(default=None, description="AI-assigned document category.")
    tags: list[str] = Field(default_factory=list, description="AI-assigned topical tags.")
    sentiment: str | None = Field(
        default=None,
        description="Overall document sentiment: positive, negative, neutral, or mixed.",
    )


class DocumentListResponse(BaseModel):
    """Paginated list of documents."""

    model_config = ConfigDict(json_schema_extra={"examples": [DOCUMENT_LIST_EXAMPLE]})

    items: list[DocumentSummary]
    total: int = Field(description="Total documents matching the query (across all pages).")
    page: int = Field(description="Current page number (1-based).")
    page_size: int = Field(description="Maximum items per page.")


class DocumentVersionSummary(BaseModel):
    """Summary of a single version within a document group."""

    id: UUID
    filename: str
    version_number: int
    is_latest: bool
    status: DocumentStatus
    created_at: datetime


class DocumentVersionListResponse(BaseModel):
    """Response listing all versions of a document group."""

    document_group_id: UUID
    items: list[DocumentVersionSummary]
    total: int
