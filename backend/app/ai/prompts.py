SUMMARY_SYSTEM_PROMPT = """You analyze documents and return concise structured output.
Respond with JSON only in this shape:
{"summary": "2-3 sentence overview", "insights": ["key point 1", "key point 2", "key point 3"]}
"""

SUMMARY_USER_PROMPT = """Document excerpt:
{text}

Generate a summary and 3-5 key insights from this content."""


def build_summary_prompt(text: str, max_chars: int = 12000) -> tuple[str, str]:
    excerpt = text[:max_chars]
    return SUMMARY_SYSTEM_PROMPT, SUMMARY_USER_PROMPT.format(text=excerpt)


CHAT_SYSTEM_PROMPT = """You are a helpful assistant that answers questions about one or more documents.
Rules:
- Answer ONLY using the provided context sources.
- If the answer is not in the context, say: "I don't have enough information in these documents."
- Be concise and accurate.
- Reference sources inline as [Source N] when using information from a source.
"""

CHAT_USER_PROMPT = """Context:
{context}

Conversation history:
{history}

Question: {question}
"""


FOLLOWUP_SYSTEM_PROMPT = """You suggest helpful follow-up questions about a document conversation.
Respond with JSON only: {"followups": ["question 1", "question 2", "question 3"]}
Each follow-up must be short (under 80 chars), specific, and different from the original question."""

FOLLOWUP_USER_PROMPT = """Original question: {question}
Assistant answer: {answer}

Suggest 3 follow-up questions the user might ask next."""


def build_followup_prompt(question: str, answer: str) -> tuple[str, str]:
    return FOLLOWUP_SYSTEM_PROMPT, FOLLOWUP_USER_PROMPT.format(question=question, answer=answer)


def build_chat_prompt(
    question: str,
    context_blocks: list[str],
    history_blocks: list[str],
) -> tuple[str, str]:
    context = "\n\n".join(context_blocks) if context_blocks else "No relevant context found."
    history = "\n".join(history_blocks) if history_blocks else "No previous messages."
    return CHAT_SYSTEM_PROMPT, CHAT_USER_PROMPT.format(
        context=context,
        history=history,
        question=question,
    )
