"""
Prompt orchestration — composes atomic prompt modules into final prompts.
"""

from app.ai.prompts.system import IDENTITY, SECURITY_RULES, TONE
from app.ai.prompts.grounding import GROUNDING_RULES, NO_CONTEXT_HANDLING
from app.ai.prompts.conversation import GREETING, DIALOGUE_FLOW
from app.ai.prompts.generation import (
    COMPARISON_SYSTEM,
    COMPARISON_USER,
    DOCUMENT_ANALYSIS_SYSTEM,
    DOCUMENT_ANALYSIS_USER,
    FOLLOWUP_SYSTEM,
    FOLLOWUP_USER,
    SESSION_TITLE_SYSTEM,
    SESSION_TITLE_USER,
    LENGTH_INSTRUCTIONS,
    SUMMARY_CUSTOM_SYSTEM,
    SUMMARY_CUSTOM_USER,
    TONE_INSTRUCTIONS,
    CONTEXTUALIZE_SYSTEM,
    CHAT_USER,
    RAG_GROUNDING_SUFFIX,
)

_CHAT_SYSTEM_PROMPT = "\n\n".join([
    IDENTITY,
    GREETING,
    DIALOGUE_FLOW,
    GROUNDING_RULES,
    NO_CONTEXT_HANDLING,
    SECURITY_RULES,
    TONE,
])


def get_chat_system_prompt() -> str:
    """Return the assembled system prompt for document chat sessions."""
    return _CHAT_SYSTEM_PROMPT


def get_contextualize_prompt() -> str:
    """Return the system prompt used to rewrite follow-up questions into standalone queries."""
    return CONTEXTUALIZE_SYSTEM


def get_grounding_suffix() -> str:
    """Return the RAG grounding suffix appended after document context."""
    return RAG_GROUNDING_SUFFIX


def build_chat_prompt(
    question: str,
    context_blocks: list[str],
    history_blocks: list[str],
) -> tuple[str, str]:
    """Compose the system and user prompts for a grounded chat completion."""
    context = (
        "\n\n".join(context_blocks)
        if context_blocks
        else "No relevant context found in the uploaded documents."
    )
    history = "\n".join(history_blocks) if history_blocks else "No previous messages."
    return _CHAT_SYSTEM_PROMPT, CHAT_USER.format(
        context=context,
        history=history,
        question=question,
    )


def build_followup_prompt(
    question: str,
    answer: str,
    *,
    document_context: str = "No document metadata available.",
    citation_context: str = "No citations in the last answer.",
) -> tuple[str, str]:
    """Compose the prompt pair for generating follow-up question suggestions."""
    return FOLLOWUP_SYSTEM, FOLLOWUP_USER.format(
        question=question,
        answer=answer,
        document_context=document_context,
        citation_context=citation_context,
    )


def build_session_title_prompt(conversation: str) -> tuple[str, str]:
    """Compose the prompt pair for generating a short session title."""
    return SESSION_TITLE_SYSTEM, SESSION_TITLE_USER.format(conversation=conversation)


def build_summary_prompt(text: str, max_chars: int = 12000) -> tuple[str, str]:
    """Compose the prompt pair for document analysis and summarization."""
    excerpt = text[:max_chars]
    return DOCUMENT_ANALYSIS_SYSTEM, DOCUMENT_ANALYSIS_USER.format(text=excerpt)


def build_custom_summary_prompt(
    text: str,
    *,
    length: str = "standard",
    tone: str = "professional",
    focus_areas: list[str] | None = None,
    max_chars: int = 12000,
) -> tuple[str, str]:
    """Compose the prompt pair for a user-customized summary with length/tone/focus controls."""
    excerpt = text[:max_chars]
    focus_instruction = (
        ", ".join(focus_areas)
        if focus_areas
        else "General overview — no specific focus requested."
    )
    return SUMMARY_CUSTOM_SYSTEM, SUMMARY_CUSTOM_USER.format(
        text=excerpt,
        length_instruction=LENGTH_INSTRUCTIONS.get(length, LENGTH_INSTRUCTIONS["standard"]),
        tone_instruction=TONE_INSTRUCTIONS.get(tone, TONE_INSTRUCTIONS["professional"]),
        focus_instruction=focus_instruction,
    )


def build_comparison_prompt(
    document_blocks: list[tuple[str, str]],
    *,
    focus: str | None = None,
) -> tuple[str, str]:
    """Compose the prompt pair for multi-document comparison."""
    blocks = "\n\n".join(
        f"--- {label} ---\n{content[:8000]}" for label, content in document_blocks
    )
    labels = [label for label, _ in document_blocks]
    label_list = ", ".join(labels)
    focus_clause = f" with focus on: {focus}" if focus else ""
    return COMPARISON_SYSTEM, COMPARISON_USER.format(
        focus_clause=focus_clause,
        document_blocks=blocks,
        label_list=label_list,
    )
