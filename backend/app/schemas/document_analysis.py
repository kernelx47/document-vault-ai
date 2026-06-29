"""Pydantic schemas and data classes for document analysis and comparison."""

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.openapi_examples import (
    COMPARE_REQUEST_EXAMPLE,
    INSIGHTS_REGENERATE_EXAMPLE,
)

SummaryLength = Literal["brief", "standard", "detailed"]
SummaryTone = Literal["neutral", "professional", "executive", "plain"]
DocumentSentiment = Literal["positive", "negative", "neutral", "mixed"]


@dataclass(frozen=True)
class DocumentAnalysisResult:
    """Immutable result of AI analysis on a single document."""

    summary: str
    insights: list[str]
    category: str
    tags: list[str]
    sentiment: str


class InsightsRegenerateRequest(BaseModel):
    """Request body for regenerating document insights with custom parameters."""

    model_config = ConfigDict(json_schema_extra={"examples": [INSIGHTS_REGENERATE_EXAMPLE]})

    length: SummaryLength = Field(default="standard", description="Summary length preset.")
    focus_areas: list[str] = Field(
        default_factory=list,
        max_length=5,
        description="Topics to emphasize (e.g. 'renewal dates', 'liability limits').",
    )
    tone: SummaryTone = Field(default="professional", description="Writing tone for the summary.")


class DocumentCompareRequest(BaseModel):
    """Request body for comparing two or more documents."""

    model_config = ConfigDict(json_schema_extra={"examples": [COMPARE_REQUEST_EXAMPLE]})

    document_ids: list[UUID] = Field(
        min_length=2,
        max_length=10,
        description="Two or more ready document IDs to compare.",
    )
    focus: str | None = Field(
        default=None,
        max_length=500,
        description="Optional comparison focus (e.g. 'coverage limits', 'pricing').",
    )


class ComparisonAspect(BaseModel):
    """A single dimension in a structured document comparison table."""

    aspect: str = Field(description="Dimension being compared.")
    values: dict[str, str] = Field(description="Per-document values keyed by document ID.")


class DocumentCompareResponse(BaseModel):
    """Response containing a structured comparison of multiple documents."""

    summary: str = Field(description="Executive comparison overview.")
    similarities: list[str] = Field(default_factory=list)
    differences: list[str] = Field(default_factory=list)
    comparison_table: list[ComparisonAspect] = Field(default_factory=list)
    recommendation: str | None = Field(default=None)
    document_filenames: dict[str, str] = Field(default_factory=dict)
