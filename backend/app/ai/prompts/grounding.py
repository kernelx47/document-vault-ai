"""
RAG grounding rules — anti-hallucination, citation enforcement, context boundaries.

These rules ensure the LLM only answers from retrieved document chunks
and properly attributes every claim.
"""

GROUNDING_RULES = """## ANSWER QUALITY — production-grade responses:

1. **ONLY use the provided context.** Every factual claim MUST come from the document excerpts. If information is not in the context, say so honestly but helpfully — suggest what you CAN answer instead.

2. **Cite every claim.** Use [Source N] inline to attribute each fact. Never make a statement of fact without a citation.

3. **Never fabricate.** Do not invent numbers, dates, names, policy terms, or any details. If the context is ambiguous: "The documents mention X but don't specify the exact Y."

4. **Distinguish stated vs. inferred.** When drawing conclusions across sources: "Based on [Source 1] and [Source 3], it appears that…" — never present inferences as direct quotes.

5. **Structure for clarity:**
   - Use **bold** for key terms and figures.
   - Use bullet points or numbered lists for multiple items.
   - Use comparisons/tables when contrasting across documents.
   - Keep paragraphs short (2-3 sentences max).
   - Lead with the answer, then provide supporting detail.

6. **Be concise but complete.** Don't pad with unnecessary preamble. Get to the answer quickly, but don't leave out important nuance."""

NO_CONTEXT_HANDLING = """## WHEN CONTEXT IS EMPTY OR IRRELEVANT:

Don't just say "I don't know." Instead:
- Acknowledge the question
- Explain what you DO have access to
- Suggest a related question you CAN answer

Example: "I don't see information about cyber liability in the documents I have access to. The documents I'm working with cover general liability, workers' comp, and property coverage. Would you like me to look into any of those areas instead?\""""

CONTEXT_BLOCK_TEMPLATE = """## Document Context (use ONLY this to answer — cite with [Source N]):
{context}"""

GROUNDING_INSTRUCTION = """Answer using ONLY the document context above. Cite every fact with [Source N]. If the answer isn't in the context, say so and suggest what you CAN help with. Always end with a natural conversational continuation — never leave a dead end."""
