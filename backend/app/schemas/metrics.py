from pydantic import BaseModel, ConfigDict, Field

from app.schemas.openapi_examples import DOCUMENT_METRICS_EXAMPLE, PROCESSING_METRICS_EXAMPLE


class DocumentMetricsResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [DOCUMENT_METRICS_EXAMPLE]})

    total: int
    pending: int
    processing: int
    ready: int
    failed: int
    total_size_bytes: int = 0
    total_chunks: int = 0


class StageMetrics(BaseModel):
    stage: str
    completed: int = 0
    failed: int = 0
    avg_duration_ms: float | None = None


class ProcessingMetricsResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [PROCESSING_METRICS_EXAMPLE]})

    total_jobs: int
    started: int = 0
    completed: int = 0
    failed: int = 0
    avg_duration_ms: float | None = None
    failure_rate: float = Field(ge=0.0, le=1.0)
    by_stage: list[StageMetrics] = Field(default_factory=list)
