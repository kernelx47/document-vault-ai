from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


SummaryLength = Literal["brief", "standard", "detailed"]
SummaryTone = Literal["neutral", "professional", "executive", "plain"]
DocumentSentiment = Literal["positive", "negative", "neutral", "mixed"]


@dataclass(frozen=True)
class DocumentAnalysisResult:
    summary: str
    insights: list[str]
    category: str
    tags: list[str]
    sentiment: str


class InsightsRegenerateRequest(BaseModel):
    length: SummaryLength = Field(default="standard", description="Summary length preset.")
    focus_areas: list[str] = Field(
        default_factory=list,
        max_length=5,
        description="Topics to emphasize (e.g. 'renewal dates', 'liability limits').",
    )
    tone: SummaryTone = Field(default="professional", description="Writing tone for the summary.")


class DocumentCompareRequest(BaseModel):
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
    aspect: str = Field(description="Dimension being compared.")
    values: dict[str, str] = Field(description="Per-document values keyed by document ID.")


class DocumentCompareResponse(BaseModel):
    summary: str = Field(description="Executive comparison overview.")
    similarities: list[str] = Field(default_factory=list)
    differences: list[str] = Field(default_factory=list)
    comparison_table: list[ComparisonAspect] = Field(default_factory=list)
    recommendation: str | None = Field(default=None)
    document_filenames: dict[str, str] = Field(default_factory=dict)
