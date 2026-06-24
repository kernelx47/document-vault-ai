from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings import get_embedding_provider
from app.ai.llm import generate_chat_answer
from app.ai.prompts import build_chat_prompt
from app.config import get_settings
from app.models import ChatMessage, DocumentChunk, MessageRole
from app.schemas.chat import Citation


@dataclass
class RetrievedChunk:
    chunk: DocumentChunk
    score: float


async def retrieve_chunks(
    db: AsyncSession, document_id: UUID, question: str
) -> list[RetrievedChunk]:
    settings = get_settings()
    provider = get_embedding_provider()
    query_embedding = provider.embed_query(question)

    distance = DocumentChunk.embedding.cosine_distance(query_embedding)
    stmt = (
        select(DocumentChunk, (1 - distance).label("score"))
        .where(DocumentChunk.document_id == document_id)
        .where(DocumentChunk.embedding.isnot(None))
        .order_by(distance)
        .limit(settings.rag_top_k)
    )
    result = await db.execute(stmt)
    rows = result.all()

    retrieved = [RetrievedChunk(chunk=row[0], score=float(row[1])) for row in rows]
    return [item for item in retrieved if item.score >= 0.2]


def build_context_blocks(retrieved: list[RetrievedChunk]) -> list[str]:
    blocks: list[str] = []
    for index, item in enumerate(retrieved, start=1):
        page = item.chunk.page_number
        page_label = f"page {page}" if page is not None else "page unknown"
        blocks.append(f"[Source {index}] ({page_label}): {item.chunk.content}")
    return blocks


def build_history_blocks(messages: list[ChatMessage], limit: int = 4) -> list[str]:
    recent = messages[-limit:] if len(messages) > limit else messages
    blocks: list[str] = []
    for message in recent:
        role = "User" if message.role == MessageRole.USER else "Assistant"
        blocks.append(f"{role}: {message.content}")
    return blocks


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
    document_id: UUID,
    question: str,
    history_messages: list[ChatMessage],
) -> tuple[str, list[Citation], list[UUID]]:
    retrieved = await retrieve_chunks(db, document_id, question)
    context_blocks = build_context_blocks(retrieved)
    history_blocks = build_history_blocks(history_messages)
    system_prompt, user_prompt = build_chat_prompt(question, context_blocks, history_blocks)
    answer = generate_chat_answer(system_prompt, user_prompt)
    citations = to_citations(retrieved)
    chunk_ids = [item.chunk.id for item in retrieved]
    return answer, citations, chunk_ids
