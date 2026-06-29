"""
Task-specific generation prompts — one per distinct LLM task.

Each prompt targets a single generation objective:
document summarization, follow-up suggestion, query contextualization, etc.
"""

# ── Document Analysis (summarize + classify + sentiment) ────────────

DOCUMENT_ANALYSIS_SYSTEM = """You analyze uploaded business documents and return structured JSON only:
{
  "summary": "overview text",
  "insights": ["key point 1", "key point 2"],
  "category": "document type",
  "tags": ["tag1", "tag2"],
  "sentiment": "positive|negative|neutral|mixed"
}

Rules:
- category: one concise label (e.g. Insurance Policy, Contract, Invoice, Proposal, Report, Certificate, Memo, Other)
- tags: 3-6 lowercase topical tags useful for search/filtering
- sentiment: overall tone of the document content (not your opinion)
- insights: 3-6 specific, factual bullet points (dates, amounts, parties, obligations, risks)
- summary: 2-3 sentence overview unless length instructions override"""

DOCUMENT_ANALYSIS_USER = """Document excerpt:
{text}

Analyze this document."""


# ── Custom Summary Regeneration ─────────────────────────────────────

SUMMARY_CUSTOM_SYSTEM = """You analyze documents and return JSON only:
{"summary": "...", "insights": ["...", "..."]}

Follow the length, tone, and focus instructions precisely."""

SUMMARY_CUSTOM_USER = """Document excerpt:
{text}

Length: {length_instruction}
Tone: {tone_instruction}
Focus areas: {focus_instruction}

Generate a summary and 3-6 insights tailored to these instructions."""


LENGTH_INSTRUCTIONS = {
    "brief": "1-2 sentences for summary; 3 insights max.",
    "standard": "2-3 sentences for summary; 4-5 insights.",
    "detailed": "1 short paragraph (4-6 sentences) for summary; 5-6 detailed insights.",
}

TONE_INSTRUCTIONS = {
    "neutral": "Objective and factual.",
    "professional": "Clear business language suitable for colleagues.",
    "executive": "Concise, decision-oriented, highlight business impact and risk.",
    "plain": "Simple language a non-expert can understand.",
}


# ── Document Summarization (default ingest — kept for compatibility) ──

SUMMARY_SYSTEM = DOCUMENT_ANALYSIS_SYSTEM

SUMMARY_USER = DOCUMENT_ANALYSIS_USER


# ── Follow-up Question Suggestions ──────────────────────────────────

FOLLOWUP_SYSTEM = """You suggest helpful follow-up questions that continue a natural conversation about uploaded documents.
Respond with JSON only: {"followups": ["question 1", "question 2", "question 3"]}
Rules:
- Each question must be under 80 characters
- Questions must be specific and directly answerable from the documents discussed
- Use document names, facts, and cited excerpts when helpful
- Make them feel like natural next steps in the conversation, not generic
- Vary the type: one detail question, one comparison question, one broader question"""

FOLLOWUP_USER = """Documents in this session:
{document_context}

Sources cited in the last answer:
{citation_context}

Original question: {question}
Assistant answer: {answer}

Suggest 3 follow-up questions the user might naturally ask next."""


# ── Document Comparison ─────────────────────────────────────────────

COMPARISON_SYSTEM = """You compare multiple documents and return JSON only:
{
  "summary": "executive overview",
  "similarities": ["..."],
  "differences": ["..."],
  "comparison_table": [
    {"aspect": "Dimension name", "values": {"doc_label_1": "value", "doc_label_2": "value"}}
  ],
  "recommendation": "optional actionable recommendation"
}

Rules:
- Use the exact doc labels provided in the user message as keys in comparison_table values
- comparison_table: 4-8 meaningful comparison dimensions
- Be specific with numbers, dates, and named parties when present
- recommendation: only when documents support a clear conclusion"""


COMPARISON_USER = """Compare these documents{focus_clause}:

{document_blocks}

Use these exact labels as keys in comparison_table values:
{label_list}"""


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
