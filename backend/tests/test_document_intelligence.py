import uuid
from unittest.mock import patch

import pytest

from app.ai.llm import analyze_document
from app.models import Document, DocumentChunk, DocumentStatus
from app.schemas.document_analysis import DocumentCompareRequest, InsightsRegenerateRequest
from app.services import comparison_service, document_service


@pytest.fixture
async def analyzed_document(db_session):
    document = Document(
        id=uuid.uuid4(),
        filename="policy.pdf",
        content_type="application/pdf",
        file_path="/tmp/policy.pdf",
        file_size_bytes=100,
        status=DocumentStatus.READY,
        summary="GL policy with $2M limit.",
        insights=["Limit is $2M", "Renewal December 2025"],
        category="Insurance Policy",
        tags=["general liability", "renewal"],
        sentiment="neutral",
        chunk_count=1,
    )
    chunk = DocumentChunk(
        id=uuid.uuid4(),
        document_id=document.id,
        chunk_index=0,
        content="General liability limit is $2M. Renewal date December 2025.",
        page_number=1,
        embedding=[0.0] * 384,
    )
    db_session.add(document)
    db_session.add(chunk)
    await db_session.commit()
    return document


def test_analyze_document_fallback():
    result = analyze_document("Premium is $10,000 per year. Renewal in June 2026.")
    assert result.summary
    assert result.insights
    assert result.category
    assert result.tags
    assert result.sentiment in {"positive", "negative", "neutral", "mixed"}


@patch("app.ai.llm._invoke_json_llm")
def test_analyze_document_parses_llm_payload(mock_invoke):
    mock_invoke.return_value = """{
        "summary": "A renewal policy.",
        "insights": ["Renewal in June"],
        "category": "Insurance Policy",
        "tags": ["renewal", "premium"],
        "sentiment": "neutral"
    }"""
    result = analyze_document("Renewal in June 2026.")
    assert result.summary == "A renewal policy."
    assert result.category == "Insurance Policy"
    assert "renewal" in result.tags


@pytest.mark.asyncio
async def test_get_insights_includes_metadata(db_session, analyzed_document):
    insights = await document_service.get_document_insights(db_session, analyzed_document.id)
    assert insights.category == "Insurance Policy"
    assert insights.sentiment == "neutral"
    assert "renewal" in insights.tags


@pytest.mark.asyncio
@patch("app.services.document_service.regenerate_custom_summary", return_value=("Short summary.", ["Point A"]))
async def test_regenerate_insights(mock_regen, db_session, analyzed_document):
    payload = InsightsRegenerateRequest(length="brief", tone="executive", focus_areas=["renewal"])
    result = await document_service.regenerate_document_insights(db_session, analyzed_document.id, payload)
    assert result.summary == "Short summary."
    assert result.category == "Insurance Policy"
    mock_regen.assert_called_once()


@pytest.mark.asyncio
@patch("app.services.comparison_service.compare_documents")
async def test_compare_documents_endpoint(mock_compare, db_session, analyzed_document):
    other = Document(
        id=uuid.uuid4(),
        filename="quote.pdf",
        content_type="application/pdf",
        file_path="/tmp/quote.pdf",
        file_size_bytes=100,
        status=DocumentStatus.READY,
        summary="Carrier B quote at $112,900.",
        insights=["Lowest premium"],
        category="Quote Comparison",
        tags=["quote"],
        sentiment="positive",
        chunk_count=0,
    )
    db_session.add(other)
    await db_session.commit()

    mock_compare.return_value = {
        "summary": "Policy vs quote comparison.",
        "similarities": ["Both mention GL"],
        "differences": ["Premium differs"],
        "comparison_table": [
            {
                "aspect": "Premium",
                "values": {
                    analyzed_document.filename: "$2M limit policy",
                    other.filename: "$112,900 quote",
                },
            }
        ],
        "recommendation": "Review quote details.",
    }

    result = await comparison_service.compare_document_set(
        db_session,
        DocumentCompareRequest(document_ids=[analyzed_document.id, other.id], focus="premium"),
    )
    assert result.summary
    assert len(result.comparison_table) == 1
    assert str(analyzed_document.id) in result.comparison_table[0].values
