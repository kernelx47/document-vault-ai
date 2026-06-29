import json
import logging
import re

from app.ai.prompts import (
    build_comparison_prompt,
    build_custom_summary_prompt,
    build_followup_prompt,
    build_session_title_prompt,
    build_summary_prompt,
)
from app.config import get_settings
from app.schemas.document_analysis import DocumentAnalysisResult
from app.services.ai_usage_service import estimate_tokens, record_ai_usage_sync

logger = logging.getLogger("app.llm")

_VALID_SENTIMENTS = {"positive", "negative", "neutral", "mixed"}


def _record_llm_usage(operation: str, provider: str, model: str, input_text: str, output_text: str) -> None:
    record_ai_usage_sync(
        operation=operation,
        provider=provider,
        model=model,
        input_tokens=estimate_tokens(input_text),
        output_tokens=estimate_tokens(output_text),
    )


def generate_summary_and_insights(text: str) -> tuple[str, list[str]]:
    result = analyze_document(text)
    return result.summary, result.insights


def analyze_document(text: str) -> DocumentAnalysisResult:
    if not text.strip():
        return DocumentAnalysisResult("", [], "Other", [], "neutral")

    try:
        content = _invoke_json_llm(build_summary_prompt(text), operation="summarize")
        return _parse_analysis_response(content, text)
    except Exception:
        logger.warning("LLM document analysis failed — using extractive fallback", exc_info=True)

    return _analysis_fallback(text)


def regenerate_custom_summary(
    text: str,
    *,
    length: str = "standard",
    tone: str = "professional",
    focus_areas: list[str] | None = None,
) -> tuple[str, list[str]]:
    if not text.strip():
        return "", []

    try:
        prompts = build_custom_summary_prompt(
            text, length=length, tone=tone, focus_areas=focus_areas
        )
        content = _invoke_json_llm(prompts, operation="summary_regenerate")
        summary, insights = _parse_summary_response(content, text)
        return summary, insights
    except Exception:
        logger.warning("Custom summary regeneration failed — using fallback", exc_info=True)
        return _generate_fallback(text)


def compare_documents(
    document_blocks: list[tuple[str, str]],
    *,
    focus: str | None = None,
) -> dict:
    if len(document_blocks) < 2:
        raise ValueError("At least two documents are required for comparison.")

    try:
        content = _invoke_json_llm(
            build_comparison_prompt(document_blocks, focus=focus),
            operation="compare",
            temperature=0.2,
        )
        parsed = _parse_json_payload(content)
        if parsed:
            return parsed
    except Exception:
        logger.warning("Document comparison failed — using fallback", exc_info=True)

    labels = [label for label, _ in document_blocks]
    return {
        "summary": f"Comparison across {len(labels)} documents: {', '.join(labels)}.",
        "similarities": [],
        "differences": ["Detailed comparison requires a configured LLM provider."],
        "comparison_table": [],
        "recommendation": None,
    }


def _invoke_json_llm(
    prompts: tuple[str, str],
    *,
    operation: str,
    temperature: float = 0.2,
) -> str:
    system_prompt, user_prompt = prompts
    settings = get_settings()

    if settings.llm_provider == "openai" and settings.openai_api_key:
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=temperature,
        )
        provider, model = "openai", settings.openai_model
    elif settings.llm_provider == "gemini" and settings.gemini_api_key:
        from langchain_google_genai import ChatGoogleGenerativeAI

        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=settings.gemini_api_key,
            temperature=temperature,
        )
        provider, model = "gemini", "gemini-2.0-flash"
    else:
        raise RuntimeError("No LLM provider configured")

    response = llm.invoke(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    )
    content = response.content if isinstance(response.content, str) else str(response.content)
    _record_llm_usage(operation, provider, model, system_prompt + user_prompt, content)
    return content


def _generate_fallback(text: str) -> tuple[str, list[str]]:
    cleaned = " ".join(text.split())
    summary = cleaned[:500] + ("..." if len(cleaned) > 500 else "")
    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    insights = [sentence.strip() for sentence in sentences[:5] if len(sentence.strip()) > 20]
    return summary, insights


def _analysis_fallback(text: str) -> DocumentAnalysisResult:
    summary, insights = _generate_fallback(text)
    return DocumentAnalysisResult(
        summary=summary,
        insights=insights,
        category="Other",
        tags=["document"],
        sentiment="neutral",
    )


def _parse_json_payload(content: str) -> dict | None:
    try:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        payload = json.loads(match.group(0) if match else content)
        return payload if isinstance(payload, dict) else None
    except (json.JSONDecodeError, AttributeError):
        return None


def _parse_analysis_response(content: str, fallback_text: str) -> DocumentAnalysisResult:
    payload = _parse_json_payload(content)
    if not payload:
        return _analysis_fallback(fallback_text)

    summary = str(payload.get("summary", "")).strip()
    insights_raw = payload.get("insights", [])
    insights = [str(item).strip() for item in insights_raw if str(item).strip()]
    category = str(payload.get("category", "Other")).strip() or "Other"
    tags_raw = payload.get("tags", [])
    tags = [str(item).strip().lower() for item in tags_raw if str(item).strip()][:6]
    sentiment = str(payload.get("sentiment", "neutral")).strip().lower()
    if sentiment not in _VALID_SENTIMENTS:
        sentiment = "neutral"

    if not summary:
        return _analysis_fallback(fallback_text)

    return DocumentAnalysisResult(
        summary=summary,
        insights=insights,
        category=category,
        tags=tags or ["document"],
        sentiment=sentiment,
    )


def _parse_summary_response(content: str, fallback_text: str) -> tuple[str, list[str]]:
    payload = _parse_json_payload(content)
    if not payload:
        return _generate_fallback(fallback_text)

    summary = str(payload.get("summary", "")).strip()
    insights_raw = payload.get("insights", [])
    insights = [str(item).strip() for item in insights_raw if str(item).strip()]
    if summary:
        return summary, insights
    return _generate_fallback(fallback_text)


def generate_chat_answer(system_prompt: str, user_prompt: str) -> str:
    settings = get_settings()

    if settings.llm_provider == "openai" and settings.openai_api_key:
        return _chat_with_openai(system_prompt, user_prompt)
    if settings.llm_provider == "gemini" and settings.gemini_api_key:
        return _chat_with_gemini(system_prompt, user_prompt)

    return _chat_fallback(user_prompt)


def get_chat_llm():
    settings = get_settings()

    if settings.llm_provider == "openai" and settings.openai_api_key:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=0.2,
        )
    if settings.llm_provider == "gemini" and settings.gemini_api_key:
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=settings.gemini_api_key,
            temperature=0.2,
        )
    return None


def _chat_with_openai(system_prompt: str, user_prompt: str) -> str:
    from langchain_openai import ChatOpenAI

    settings = get_settings()
    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.2,
    )
    response = llm.invoke(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    )
    content = response.content if isinstance(response.content, str) else str(response.content)
    _record_llm_usage("chat", "openai", settings.openai_model, system_prompt + user_prompt, content)
    return content


def _chat_with_gemini(system_prompt: str, user_prompt: str) -> str:
    from langchain_google_genai import ChatGoogleGenerativeAI

    settings = get_settings()
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=settings.gemini_api_key,
        temperature=0.2,
    )
    response = llm.invoke(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    )
    content = response.content if isinstance(response.content, str) else str(response.content)
    _record_llm_usage("chat", "gemini", "gemini-2.0-flash", system_prompt + user_prompt, content)
    return content


def _chat_fallback(user_prompt: str) -> str:
    if "Question:" not in user_prompt:
        return "I don't have enough information in these documents."
    context_section = user_prompt.split("Question:", maxsplit=1)[0]
    if "No relevant context found" in context_section:
        return "I don't have enough information in these documents."
    excerpt = context_section.strip()[:600]
    return f"Based on the document context: {excerpt}"


def stream_chat_answer(system_prompt: str, user_prompt: str):
    settings = get_settings()

    if settings.llm_provider == "openai" and settings.openai_api_key:
        yield from _stream_chat_with_openai(system_prompt, user_prompt)
        return
    if settings.llm_provider == "gemini" and settings.gemini_api_key:
        yield from _stream_chat_with_gemini(system_prompt, user_prompt)
        return

    yield _chat_fallback(user_prompt)


def _stream_chat_with_openai(system_prompt: str, user_prompt: str):
    from langchain_openai import ChatOpenAI

    settings = get_settings()
    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.2,
    )
    parts: list[str] = []
    for chunk in llm.stream(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    ):
        content = chunk.content if isinstance(chunk.content, str) else str(chunk.content)
        if content:
            parts.append(content)
            yield content
    _record_llm_usage("chat_stream", "openai", settings.openai_model, system_prompt + user_prompt, "".join(parts))


def _stream_chat_with_gemini(system_prompt: str, user_prompt: str):
    from langchain_google_genai import ChatGoogleGenerativeAI

    settings = get_settings()
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=settings.gemini_api_key,
        temperature=0.2,
    )
    parts: list[str] = []
    for chunk in llm.stream(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    ):
        content = chunk.content if isinstance(chunk.content, str) else str(chunk.content)
        if content:
            parts.append(content)
            yield content
    _record_llm_usage("chat_stream", "gemini", "gemini-2.0-flash", system_prompt + user_prompt, "".join(parts))


def generate_followup_suggestions(
    question: str,
    answer: str,
    *,
    document_context: str = "",
    citation_context: str = "",
) -> list[str]:
    settings = get_settings()
    kwargs = {
        "document_context": document_context or "No document metadata available.",
        "citation_context": citation_context or "No citations in the last answer.",
    }

    if settings.llm_provider == "openai" and settings.openai_api_key:
        suggestions = _followups_with_openai(question, answer, **kwargs)
        if suggestions:
            return suggestions
    if settings.llm_provider == "gemini" and settings.gemini_api_key:
        suggestions = _followups_with_gemini(question, answer, **kwargs)
        if suggestions:
            return suggestions

    return _followup_fallback(question)


def generate_session_title(conversation: str) -> str | None:
    settings = get_settings()

    if settings.llm_provider == "openai" and settings.openai_api_key:
        title = _session_title_with_openai(conversation)
        if title is not None:
            return title
    if settings.llm_provider == "gemini" and settings.gemini_api_key:
        title = _session_title_with_gemini(conversation)
        if title is not None:
            return title

    return None


def _parse_session_title(content: str) -> str | None:
    try:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        payload = json.loads(match.group(0) if match else content)
        title = str(payload.get("title", "")).strip()
        return title or None
    except (json.JSONDecodeError, AttributeError):
        return None


def _session_title_with_openai(conversation: str) -> str | None:
    from langchain_openai import ChatOpenAI

    settings = get_settings()
    system_prompt, user_prompt = build_session_title_prompt(conversation)
    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.3,
    )
    response = llm.invoke(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    )
    content = response.content if isinstance(response.content, str) else str(response.content)
    _record_llm_usage("session_title", "openai", settings.openai_model, system_prompt + user_prompt, content)
    return _parse_session_title(content)


def _session_title_with_gemini(conversation: str) -> str | None:
    from langchain_google_genai import ChatGoogleGenerativeAI

    settings = get_settings()
    system_prompt, user_prompt = build_session_title_prompt(conversation)
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=settings.gemini_api_key,
        temperature=0.3,
    )
    response = llm.invoke(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    )
    content = response.content if isinstance(response.content, str) else str(response.content)
    _record_llm_usage("session_title", "gemini", "gemini-2.0-flash", system_prompt + user_prompt, content)
    return _parse_session_title(content)


def _parse_followups(content: str) -> list[str]:
    try:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        payload = json.loads(match.group(0) if match else content)
        followups = payload.get("followups", [])
        return [str(item).strip() for item in followups if str(item).strip()][:3]
    except (json.JSONDecodeError, AttributeError):
        return []


def _followups_with_openai(
    question: str,
    answer: str,
    *,
    document_context: str,
    citation_context: str,
) -> list[str]:
    from langchain_openai import ChatOpenAI

    settings = get_settings()
    system_prompt, user_prompt = build_followup_prompt(
        question,
        answer,
        document_context=document_context,
        citation_context=citation_context,
    )
    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.4,
    )
    response = llm.invoke(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    )
    content = response.content if isinstance(response.content, str) else str(response.content)
    _record_llm_usage("followups", "openai", settings.openai_model, system_prompt + user_prompt, content)
    return _parse_followups(content)


def _followups_with_gemini(
    question: str,
    answer: str,
    *,
    document_context: str,
    citation_context: str,
) -> list[str]:
    from langchain_google_genai import ChatGoogleGenerativeAI

    settings = get_settings()
    system_prompt, user_prompt = build_followup_prompt(
        question,
        answer,
        document_context=document_context,
        citation_context=citation_context,
    )
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=settings.gemini_api_key,
        temperature=0.4,
    )
    response = llm.invoke(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    )
    content = response.content if isinstance(response.content, str) else str(response.content)
    _record_llm_usage("followups", "gemini", "gemini-2.0-flash", system_prompt + user_prompt, content)
    return _parse_followups(content)


def _followup_fallback(question: str) -> list[str]:
    return [
        "Can you summarize the key points?",
        "What dates or deadlines are mentioned?",
        f"Can you explain more about: {question[:60]}?",
    ]
