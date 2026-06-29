"""Pydantic schema for the service health-check endpoint."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.openapi_examples import HEALTH_EXAMPLE

CheckStatus = Literal["ok", "error"]
HealthStatus = Literal["ok", "degraded"]


class HealthResponse(BaseModel):
    """Response reporting the health status of the API and its dependencies."""

    model_config = ConfigDict(json_schema_extra={"examples": [HEALTH_EXAMPLE]})

    service: str = Field(description="Service identifier.")
    api: Literal["ok"] = Field(description="API process is running.")
    database: CheckStatus = Field(description="PostgreSQL connectivity.")
    redis: CheckStatus = Field(description="Redis connectivity.")
    worker: CheckStatus = Field(description="Celery worker responsiveness.")
    status: HealthStatus = Field(
        description="Overall health: `ok` when all dependencies are healthy, otherwise `degraded`."
    )
