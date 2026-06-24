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
        return "I don't have enough information in this document."
    context_section = user_prompt.split("Question:", maxsplit=1)[0]
    if "No relevant context found" in context_section:
        return "I don't have enough information in this document."
    excerpt = context_section.strip()[:600]
    return f"Based on the document context: {excerpt}"
