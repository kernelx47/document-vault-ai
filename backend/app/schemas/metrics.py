"""Pydantic schemas for platform metrics and analytics endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ProcessingJobStatus
from app.schemas.openapi_examples import (
    DOCUMENT_METRICS_EXAMPLE,
    PROCESSING_HISTORY_EXAMPLE,
    PROCESSING_METRICS_EXAMPLE,
    STORAGE_METRICS_EXAMPLE,
    SYSTEM_METRICS_EXAMPLE,
)


class DocumentMetricsResponse(BaseModel):
    """Response with aggregate document counts and storage totals."""

    model_config = ConfigDict(json_schema_extra={"examples": [DOCUMENT_METRICS_EXAMPLE]})

    total: int = Field(description="Total documents in the vault.")
    pending: int = Field(description="Documents waiting to be processed.")
    processing: int = Field(description="Documents currently being processed.")
    ready: int = Field(description="Documents available for chat.")
    failed: int = Field(description="Documents that failed processing.")
    total_size_bytes: int = Field(default=0, description="Combined size of all uploaded files.")
    total_chunks: int = Field(default=0, description="Total indexed chunks across all documents.")


class RouteLatencyMetrics(BaseModel):
    """Latency statistics for a single API route."""

    route: str = Field(description="HTTP method and normalized path (UUIDs replaced with `{id}`).")
    avg_duration_ms: float | None = Field(default=None, description="Average response time for this route.")
    p95_duration_ms: float | None = Field(default=None, description="95th percentile response time for this route.")
    sample_count: int = Field(default=0, description="Number of latency samples for this route.")


class ChatMetrics(BaseModel):
    """Rolling performance metrics for chat and RAG operations."""

    total_requests: int = Field(default=0, description="Chat/RAG requests in the rolling sample window.")
    error_count: int = Field(default=0, description="Chat/RAG requests that failed in the sample window.")
    error_rate: float = Field(ge=0.0, le=1.0, description="Ratio of failed chat/RAG requests (0.0–1.0).")
    avg_rag_duration_ms: float | None = Field(
        default=None, description="Average end-to-end RAG answer time in milliseconds."
    )
    avg_retrieval_duration_ms: float | None = Field(
        default=None, description="Average vector retrieval time in milliseconds."
    )


class StageMetrics(BaseModel):
    """Completion counts and average duration for a single pipeline stage."""

    stage: str = Field(description="Pipeline stage name (e.g. extract, embed).")
    completed: int = Field(default=0, description="Jobs completed at this stage.")
    failed: int = Field(default=0, description="Jobs that failed at this stage.")
    avg_duration_ms: float | None = Field(default=None, description="Average stage duration in milliseconds.")


class ProcessingMetricsResponse(BaseModel):
    """Response with processing pipeline job counts and per-stage breakdown."""

    model_config = ConfigDict(json_schema_extra={"examples": [PROCESSING_METRICS_EXAMPLE]})

    total_jobs: int = Field(description="Total processing jobs recorded.")
    started: int = Field(default=0, description="Jobs currently in progress.")
    completed: int = Field(default=0, description="Jobs that finished successfully.")
    failed: int = Field(default=0, description="Jobs that failed.")
    avg_duration_ms: float | None = Field(
        default=None, description="Average end-to-end processing time in milliseconds."
    )
    failure_rate: float = Field(ge=0.0, le=1.0, description="Ratio of failed jobs (0.0–1.0).")
    by_stage: list[StageMetrics] = Field(
        default_factory=list,
        description="Per-stage breakdown of completed/failed jobs and timing.",
    )


class StorageMetricsResponse(BaseModel):
    """Response with storage usage, chunk counts, and chat session totals."""

    model_config = ConfigDict(json_schema_extra={"examples": [STORAGE_METRICS_EXAMPLE]})

    total_file_bytes: int = Field(description="Sum of uploaded file sizes recorded in metadata.")
    filesystem_bytes: int | None = Field(
        default=None, description="Actual bytes on disk in the upload directory, when available."
    )
    total_chunks: int = Field(default=0, description="Indexed text chunks across all documents.")
    total_chat_sessions: int = Field(default=0, description="Total chat sessions created.")
    total_chat_messages: int = Field(default=0, description="Total chat messages stored.")
    embedding_dimension: int = Field(description="Vector dimension used for chunk embeddings.")


class ProcessingJobRecord(BaseModel):
    """Serialized representation of a single processing job for history responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    stage: str = Field(description="Pipeline stage (extract, chunk, embed, summarize).")
    status: ProcessingJobStatus
    duration_ms: int | None = Field(default=None, description="Stage duration in milliseconds.")
    error_message: str | None = Field(default=None, description="Failure reason when status is `failed`.")
    created_at: datetime


class ProcessingHistoryResponse(BaseModel):
    """Paginated list of processing job records."""

    model_config = ConfigDict(json_schema_extra={"examples": [PROCESSING_HISTORY_EXAMPLE]})

    items: list[ProcessingJobRecord] = Field(description="Processing job records, newest first.")
    total: int = Field(description="Total matching jobs.")
    limit: int = Field(description="Maximum items returned.")
    offset: int = Field(description="Pagination offset.")


class SystemMetricsResponse(BaseModel):
    """Response with API latency, worker status, and overall system health metrics."""

    model_config = ConfigDict(json_schema_extra={"examples": [SYSTEM_METRICS_EXAMPLE]})

    avg_api_latency_ms: float | None = Field(
        default=None, description="Rolling average API response time in milliseconds."
    )
    p95_api_latency_ms: float | None = Field(
        default=None, description="95th percentile API response time in milliseconds."
    )
    api_request_samples: int = Field(default=0, description="Number of requests in the latency sample.")
    api_latency_by_route: list[RouteLatencyMetrics] = Field(
        default_factory=list,
        description="Per-route latency breakdown (UUID path segments normalized to `{id}`).",
    )
    worker_queue_depth: int = Field(default=0, description="Pending Celery tasks in the queue.")
    documents_per_hour: int = Field(
        default=0,
        description="Documents that finished processing (ready or failed) in the last hour.",
    )
    document_failure_rate: float = Field(
        ge=0.0, le=1.0, description="Ratio of documents with `failed` status."
    )
    processing_failure_rate: float = Field(
        ge=0.0, le=1.0, description="Ratio of processing jobs that failed."
    )
    avg_processing_duration_ms: float | None = Field(
        default=None, description="Average document processing duration in milliseconds."
    )
    stage_avg_duration_ms: list[StageMetrics] = Field(
        default_factory=list,
        description="Average duration per pipeline stage.",
    )
    chat: ChatMetrics = Field(description="Rolling chat/RAG performance metrics.")


class AIUsageByOperation(BaseModel):
    """AI token usage and cost breakdown for a single operation type."""

    operation: str
    requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0


class AIUsageByProvider(BaseModel):
    """AI token usage and cost breakdown for a single provider."""

    provider: str
    requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0


class AIUsageMetricsResponse(BaseModel):
    """Response with aggregate AI usage, quotas, and per-operation/provider breakdowns."""

    total_requests: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    daily_request_count: int = 0
    daily_request_quota: int | None = None
    daily_quota_remaining: int | None = None
    by_operation: list[AIUsageByOperation] = Field(default_factory=list)
    by_provider: list[AIUsageByProvider] = Field(default_factory=list)


class AIUsageTimeSeriesPoint(BaseModel):
    """A single time-series data point for AI usage metrics."""

    label: str = Field(description="Human-readable hour bucket label.")
    requests: int = 0
    tokens: int = 0
    cost_usd: float = 0.0


class ProcessingTimeSeriesPoint(BaseModel):
    """A single time-series data point for processing job outcomes."""

    label: str = Field(description="Human-readable hour bucket label.")
    completed: int = 0
    failed: int = 0


class MetricsTimeseriesResponse(BaseModel):
    """Response containing time-series data for AI usage, latency, and processing."""

    ai_usage: list[AIUsageTimeSeriesPoint] = Field(default_factory=list)
    api_latency_ms: list[float] = Field(
        default_factory=list,
        description="Recent API latency samples in milliseconds, oldest first.",
    )
    processing_jobs: list[ProcessingTimeSeriesPoint] = Field(default_factory=list)
