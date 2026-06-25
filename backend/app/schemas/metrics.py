from pydantic import BaseModel, Field


class DocumentMetricsResponse(BaseModel):
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
    total_jobs: int
    started: int = 0
    completed: int = 0
    failed: int = 0
    avg_duration_ms: float | None = None
    failure_rate: float = Field(ge=0.0, le=1.0)
    by_stage: list[StageMetrics] = Field(default_factory=list)
