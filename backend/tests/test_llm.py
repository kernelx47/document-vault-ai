from unittest.mock import patch

from app.ai.llm import generate_summary_and_insights


@patch("app.ai.llm._generate_with_openai")
def test_generate_summary_uses_openai_when_configured(mock_openai):
    mock_openai.return_value = ("Summary text", ["Insight one"])

    with patch("app.ai.llm.get_settings") as mock_settings:
        mock_settings.return_value.llm_provider = "openai"
        mock_settings.return_value.openai_api_key = "sk-test"
        mock_settings.return_value.gemini_api_key = ""

        summary, insights = generate_summary_and_insights("Document body")

    assert summary == "Summary text"
    assert insights == ["Insight one"]
    mock_openai.assert_called_once_with("Document body")
