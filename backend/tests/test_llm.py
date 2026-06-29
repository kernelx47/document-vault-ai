from unittest.mock import patch

from app.ai.llm import analyze_document, generate_summary_and_insights


@patch("app.ai.llm._invoke_json_llm")
def test_generate_summary_uses_openai_when_configured(mock_invoke):
    mock_invoke.return_value = """{
        "summary": "Summary text",
        "insights": ["Insight one"],
        "category": "Report",
        "tags": ["demo"],
        "sentiment": "neutral"
    }"""

    summary, insights = generate_summary_and_insights("Document body")

    assert summary == "Summary text"
    assert insights == ["Insight one"]
    mock_invoke.assert_called_once()


@patch("app.ai.llm._invoke_json_llm")
def test_analyze_document_includes_classification(mock_invoke):
    mock_invoke.return_value = """{
        "summary": "Policy overview",
        "insights": ["Limit is $2M"],
        "category": "Insurance Policy",
        "tags": ["liability"],
        "sentiment": "neutral"
    }"""

    result = analyze_document("Policy body")
    assert result.category == "Insurance Policy"
    assert result.sentiment == "neutral"
