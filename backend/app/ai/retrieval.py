from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings import get_embedding_provider
from app.config import get_settings
from app.models import ChatMessage, DocumentChunk, MessageRole


@dataclass
class RetrievedChunk:
    chunk: DocumentChunk
    score: float


async def retrieve_chunks(
    db: AsyncSession, document_ids: list[UUID], question: str
) -> list[RetrievedChunk]:
    if not document_ids:
        return []

    settings = get_settings()
    provider = get_embedding_provider()
    query_embedding = provider.embed_query(question)

    distance = DocumentChunk.embedding.cosine_distance(query_embedding)
    stmt = (
        select(DocumentChunk, (1 - distance).label("score"))
        .where(DocumentChunk.document_id.in_(document_ids))
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
