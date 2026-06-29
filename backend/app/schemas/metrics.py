from pydantic import BaseModel, ConfigDict, Field

from app.schemas.openapi_examples import (
    DOCUMENT_METRICS_EXAMPLE,
    PROCESSING_METRICS_EXAMPLE,
    SYSTEM_METRICS_EXAMPLE,
)


class DocumentMetricsResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [DOCUMENT_METRICS_EXAMPLE]})

    total: int = Field(description="Total documents in the vault.")
    pending: int = Field(description="Documents waiting to be processed.")
    processing: int = Field(description="Documents currently being processed.")
    ready: int = Field(description="Documents available for chat.")
    failed: int = Field(description="Documents that failed processing.")
    total_size_bytes: int = Field(default=0, description="Combined size of all uploaded files.")
    total_chunks: int = Field(default=0, description="Total indexed chunks across all documents.")


class StageMetrics(BaseModel):
    stage: str = Field(description="Pipeline stage name (e.g. extract, embed).")
    completed: int = Field(default=0, description="Jobs completed at this stage.")
    failed: int = Field(default=0, description="Jobs that failed at this stage.")
    avg_duration_ms: float | None = Field(default=None, description="Average stage duration in milliseconds.")


class ProcessingMetricsResponse(BaseModel):
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


class SystemMetricsResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [SYSTEM_METRICS_EXAMPLE]})

    avg_api_latency_ms: float | None = Field(
        default=None, description="Rolling average API response time in milliseconds."
    )
    api_request_samples: int = Field(default=0, description="Number of requests in the latency sample.")
    worker_queue_depth: int = Field(default=0, description="Pending Celery tasks in the queue.")
    documents_per_hour: int = Field(default=0, description="Documents successfully processed in the last hour.")
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
