from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.langchain_rag import generate_answer, stream_answer
from app.ai.retrieval import (
    RetrievedChunk,
    build_context_blocks,
    build_history_blocks,
    retrieve_chunks,
)
from app.models import ChatMessage
from app.schemas.chat import Citation

__all__ = [
    "RetrievedChunk",
    "build_context_blocks",
    "build_history_blocks",
    "retrieve_chunks",
    "generate_rag_answer",
    "prepare_rag_prompt",
    "to_citations",
]


def to_citations(retrieved: list[RetrievedChunk]) -> list[Citation]:
    citations: list[Citation] = []
    for item in retrieved:
        excerpt = item.chunk.content
        if len(excerpt) > 280:
            excerpt = excerpt[:277] + "..."
        citations.append(
            Citation(
                chunk_id=item.chunk.id,
                page_number=item.chunk.page_number,
                excerpt=excerpt,
                score=round(item.score, 4),
            )
        )
    return citations


async def generate_rag_answer(
    db: AsyncSession,
    document_ids: list[UUID],
    question: str,
    history_messages: list[ChatMessage],
) -> tuple[str, list[Citation], list[UUID]]:
    retrieved = await retrieve_chunks(db, document_ids, question)
    answer = await generate_answer(db, document_ids, question, history_messages, retrieved)
    citations = to_citations(retrieved)
    chunk_ids = [item.chunk.id for item in retrieved]
    return answer, citations, chunk_ids


async def prepare_rag_prompt(
    db: AsyncSession,
    document_ids: list[UUID],
    question: str,
    history_messages: list[ChatMessage],
) -> tuple[list[RetrievedChunk], str, str, list[Citation], list[UUID]]:
    from app.ai.prompts import build_chat_prompt

    retrieved = await retrieve_chunks(db, document_ids, question)
    context_blocks = build_context_blocks(retrieved)
    history_blocks = build_history_blocks(history_messages)
    system_prompt, user_prompt = build_chat_prompt(question, context_blocks, history_blocks)
    citations = to_citations(retrieved)
    chunk_ids = [item.chunk.id for item in retrieved]
    return retrieved, system_prompt, user_prompt, citations, chunk_ids
