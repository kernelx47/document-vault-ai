import json
import re

from app.ai.prompts import build_summary_prompt
from app.config import get_settings


def generate_summary_and_insights(text: str) -> tuple[str, list[str]]:
    settings = get_settings()
    if not text.strip():
        return "", []

    if settings.llm_provider == "openai" and settings.openai_api_key:
        return _generate_with_openai(text)
    if settings.llm_provider == "gemini" and settings.gemini_api_key:
        return _generate_with_gemini(text)

    return _generate_fallback(text)


def _generate_with_openai(text: str) -> tuple[str, list[str]]:
    from langchain_openai import ChatOpenAI

    settings = get_settings()
    system_prompt, user_prompt = build_summary_prompt(text)
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
    return _parse_summary_response(content, text)


def _generate_with_gemini(text: str) -> tuple[str, list[str]]:
    from langchain_google_genai import ChatGoogleGenerativeAI

    settings = get_settings()
    system_prompt, user_prompt = build_summary_prompt(text)
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
    return _parse_summary_response(content, text)


def _generate_fallback(text: str) -> tuple[str, list[str]]:
    cleaned = " ".join(text.split())
    summary = cleaned[:500] + ("..." if len(cleaned) > 500 else "")
    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    insights = [sentence.strip() for sentence in sentences[:5] if len(sentence.strip()) > 20]
    return summary, insights


def _parse_summary_response(content: str, fallback_text: str) -> tuple[str, list[str]]:
    try:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        payload = json.loads(match.group(0) if match else content)
        summary = str(payload.get("summary", "")).strip()
        insights_raw = payload.get("insights", [])
        insights = [str(item).strip() for item in insights_raw if str(item).strip()]
        if summary:
            return summary, insights
    except (json.JSONDecodeError, AttributeError):
        pass
    return _generate_fallback(fallback_text)


def generate_chat_answer(system_prompt: str, user_prompt: str) -> str:
    settings = get_settings()

    if settings.llm_provider == "openai" and settings.openai_api_key:
        return _chat_with_openai(system_prompt, user_prompt)
    if settings.llm_provider == "gemini" and settings.gemini_api_key:
        return _chat_with_gemini(system_prompt, user_prompt)

    return _chat_fallback(user_prompt)


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
    return response.content if isinstance(response.content, str) else str(response.content)


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
    return response.content if isinstance(response.content, str) else str(response.content)


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
    for chunk in llm.stream(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    ):
        content = chunk.content if isinstance(chunk.content, str) else str(chunk.content)
        if content:
            yield content


def _stream_chat_with_gemini(system_prompt: str, user_prompt: str):
    from langchain_google_genai import ChatGoogleGenerativeAI

    settings = get_settings()
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=settings.gemini_api_key,
        temperature=0.2,
    )
    for chunk in llm.stream(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    ):
        content = chunk.content if isinstance(chunk.content, str) else str(chunk.content)
        if content:
            yield content


def generate_followup_suggestions(question: str, answer: str) -> list[str]:
    settings = get_settings()

    if settings.llm_provider == "openai" and settings.openai_api_key:
        suggestions = _followups_with_openai(question, answer)
        if suggestions:
            return suggestions
    if settings.llm_provider == "gemini" and settings.gemini_api_key:
        suggestions = _followups_with_gemini(question, answer)
        if suggestions:
            return suggestions

    return _followup_fallback(question)


def _parse_followups(content: str) -> list[str]:
    try:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        payload = json.loads(match.group(0) if match else content)
        followups = payload.get("followups", [])
        return [str(item).strip() for item in followups if str(item).strip()][:3]
    except (json.JSONDecodeError, AttributeError):
        return []


def _followups_with_openai(question: str, answer: str) -> list[str]:
    from langchain_openai import ChatOpenAI

    from app.ai.prompts import build_followup_prompt

    settings = get_settings()
    system_prompt, user_prompt = build_followup_prompt(question, answer)
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
    return _parse_followups(content)


def _followups_with_gemini(question: str, answer: str) -> list[str]:
    from langchain_google_genai import ChatGoogleGenerativeAI

    from app.ai.prompts import build_followup_prompt

    settings = get_settings()
    system_prompt, user_prompt = build_followup_prompt(question, answer)
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
    return _parse_followups(content)


def _followup_fallback(question: str) -> list[str]:
    return [
        "Can you summarize the key points?",
        "What dates or deadlines are mentioned?",
        f"Can you explain more about: {question[:60]}?",
    ]
