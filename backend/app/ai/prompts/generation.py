"""
Task-specific generation prompts — one per distinct LLM task.

Each prompt targets a single generation objective:
document summarization, follow-up suggestion, query contextualization, etc.
"""

# ── Document Summarization ──────────────────────────────────────────

SUMMARY_SYSTEM = """You analyze documents and return concise structured output.
Respond with JSON only in this shape:
{"summary": "2-3 sentence overview", "insights": ["key point 1", "key point 2", "key point 3"]}
"""

SUMMARY_USER = """Document excerpt:
{text}

Generate a summary and 3-5 key insights from this content."""


# ── Follow-up Question Suggestions ──────────────────────────────────

FOLLOWUP_SYSTEM = """You suggest helpful follow-up questions that continue a natural conversation about uploaded documents.
Respond with JSON only: {"followups": ["question 1", "question 2", "question 3"]}
Rules:
- Each question must be under 80 characters
- Questions must be specific and directly answerable from the documents discussed
- Make them feel like natural next steps in the conversation, not generic
- Vary the type: one detail question, one comparison question, one broader question"""

FOLLOWUP_USER = """Original question: {question}
Assistant answer: {answer}

Suggest 3 follow-up questions the user might naturally ask next. They should feel like a real person continuing the conversation, not a checklist."""


# ── Query Contextualization (multi-turn rewriting) ───────────────────

CONTEXTUALIZE_SYSTEM = """Given a chat history and the latest user question which might reference
prior context, reformulate the question as a standalone question that can be
understood without the chat history. Do NOT answer the question — only
reformulate it. If it is already standalone, return it unchanged."""


# ── Chat User Prompt Template ────────────────────────────────────────

CHAT_USER = """## Document Context (use ONLY this to answer — cite with [Source N]):
{context}

## Conversation History:
{history}

## User Question:
{question}

Instructions: Answer using ONLY the document context above. Cite every fact with [Source N]. If the answer isn't in the context, say so and suggest what you CAN help with. Always end with a natural conversational continuation — never leave a dead end."""


# ── RAG Grounding Suffix (appended to LangChain chain) ───────────────

RAG_GROUNDING_SUFFIX = """

IMPORTANT: You MUST cite [Source N] for every factual claim. If no documents
are relevant, say so honestly and suggest what you CAN help with. Finish
with a warm, natural follow-up prompt — never leave a dead end."""
