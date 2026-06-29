"""Pydantic schemas for upload batch listing and detail endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DocumentStatus


class BatchDocumentSummary(BaseModel):
    """Minimal document info shown inside a batch detail response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    status: DocumentStatus
    file_size_bytes: int
    created_at: datetime


class BatchSummary(BaseModel):
    """Compact batch representation for list responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    label: str
    total_files: int = Field(description="Number of files submitted in this batch.")
    ready: int = Field(default=0, description="Documents that finished processing.")
    processing: int = Field(default=0, description="Documents currently being processed.")
    pending: int = Field(default=0, description="Documents waiting in the queue.")
    failed: int = Field(default=0, description="Documents that failed processing.")
    created_at: datetime


class BatchDetail(BatchSummary):
    """Full batch details including per-document status breakdown."""

    documents: list[BatchDocumentSummary] = Field(
        default_factory=list, description="All documents in this batch."
    )


class BatchListResponse(BaseModel):
    """Paginated list of upload batches."""

    items: list[BatchSummary]
    total: int = Field(description="Total batches (across all pages).")
    page: int
    page_size: int
