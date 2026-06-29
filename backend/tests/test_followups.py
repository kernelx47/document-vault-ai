from app.ai.llm import (
    _answer_indicates_missing_context,
    _filter_followup_suggestions,
    generate_followup_suggestions,
)


def test_detects_missing_context_answer():
    answer = (
        "I don't see any details from the policy.pdf documents in the information I have right now. "
        "If you can share specific sections, I'd be happy to help compare them for you."
    )
    assert _answer_indicates_missing_context(answer, "No citations in the last answer.")


def test_recovery_followups_when_no_citations():
    answer = "I don't have enough information in these documents to compare them."
    suggestions = generate_followup_suggestions(
        "Compare my policies",
        answer,
        document_context="- policy.pdf (Insurance Policy, sentiment: neutral)",
        citation_context="No citations in the last answer.",
        has_citations=False,
    )
    assert suggestions
    assert not any("compare" in s.lower() and "across" in s.lower() for s in suggestions)
    assert not any("main topics covered in each" in s.lower() for s in suggestions)


def test_filters_contradictory_llm_followups():
    filtered = _filter_followup_suggestions(
        [
            "What are the main topics covered in each policy.pdf file?",
            "Which document should we focus on first?",
        ],
        answer="I don't see any details from policy.pdf in what I have.",
        has_citations=False,
    )
    assert "Which document should we focus on first?" in filtered
    assert not any("main topics covered" in s.lower() for s in filtered)
