"""
Prompt orchestration — composes atomic prompt modules into final prompts.

This is the ONLY module that assembles prompts for the LLM. Other modules
define building blocks; this module wires them together. All external code
should import from here (via the package __init__).

Architecture:
  system.py        →  identity + security + tone        (WHO)
  grounding.py     →  citation + anti-hallucination     (RULES)
  conversation.py  →  dialogue flow + greeting          (HOW)
  generation.py    →  task-specific templates            (WHAT)
  orchestration.py →  assembly + context formatting      (COMPOSE)
"""

from app.ai.prompts.system import IDENTITY, SECURITY_RULES, TONE
from app.ai.prompts.grounding import GROUNDING_RULES, NO_CONTEXT_HANDLING
from app.ai.prompts.conversation import GREETING, DIALOGUE_FLOW
from app.ai.prompts.generation import (
    SUMMARY_SYSTEM,
    SUMMARY_USER,
    FOLLOWUP_SYSTEM,
    FOLLOWUP_USER,
    CONTEXTUALIZE_SYSTEM,
    CHAT_USER,
    RAG_GROUNDING_SUFFIX,
)


# ── Composed system prompt (identity + grounding + conversation + security) ──

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
    """Return the fully assembled chat system prompt."""
    return _CHAT_SYSTEM_PROMPT


def get_contextualize_prompt() -> str:
    """Return the query-rewriting system prompt for multi-turn conversations."""
    return CONTEXTUALIZE_SYSTEM


def get_grounding_suffix() -> str:
    """Return the RAG grounding suffix appended to the LangChain chain."""
    return RAG_GROUNDING_SUFFIX


# ── Builders (context formatting + assembly) ────────────────────────


def build_chat_prompt(
    question: str,
    context_blocks: list[str],
    history_blocks: list[str],
) -> tuple[str, str]:
    """Assemble a (system, user) prompt pair for a chat turn."""
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


def build_followup_prompt(question: str, answer: str) -> tuple[str, str]:
    """Assemble a (system, user) prompt pair for follow-up suggestions."""
    return FOLLOWUP_SYSTEM, FOLLOWUP_USER.format(question=question, answer=answer)


def build_summary_prompt(text: str, max_chars: int = 12000) -> tuple[str, str]:
    """Assemble a (system, user) prompt pair for document summarization."""
    excerpt = text[:max_chars]
    return SUMMARY_SYSTEM, SUMMARY_USER.format(text=excerpt)
