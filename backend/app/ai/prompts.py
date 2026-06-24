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
