"""
Prompt architecture for Document Vault AI.

Organized by concern:
  - system.py      → Core identity, persona, tone, security rules
  - grounding.py   → RAG grounding rules, citation enforcement, anti-hallucination
  - conversation.py→ Conversational flow, greeting, closing, casual handling
  - generation.py  → Task-specific generation prompts (summary, followups)
  - orchestration.py → Prompt composition, context assembly, query rewriting
"""

from app.ai.prompts.orchestration import (
    build_chat_prompt,
    build_followup_prompt,
    build_summary_prompt,
    get_chat_system_prompt,
    get_contextualize_prompt,
    get_grounding_suffix,
)

__all__ = [
    "build_chat_prompt",
    "build_followup_prompt",
    "build_summary_prompt",
    "get_chat_system_prompt",
    "get_contextualize_prompt",
    "get_grounding_suffix",
]
