"""Vector similarity retrieval of document chunks for RAG context building."""

import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings import get_embedding_provider
from app.config import get_settings
from app.models import ChatMessage, Document, DocumentChunk, MessageRole

logger = logging.getLogger("app.retrieval")


@dataclass
class RetrievedChunk:
    """A document chunk paired with its cosine similarity score."""

    chunk: DocumentChunk
    score: float
    document_filename: str | None = None


async def retrieve_chunks(
    db: AsyncSession, document_ids: list[UUID], question: str
) -> list[RetrievedChunk]:
    if not document_ids:
        return []

    settings = get_settings()

    try:
        provider = get_embedding_provider()
        query_embedding = provider.embed_query(question)
    except Exception:
        logger.exception("Failed to generate query embedding")
        raise

    if not query_embedding:
        logger.warning("Empty embedding returned for question — returning no results")
        return []

    distance = DocumentChunk.embedding.cosine_distance(query_embedding)
    stmt = (
        select(DocumentChunk, Document.filename, (1 - distance).label("score"))
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(DocumentChunk.document_id.in_(document_ids))
        .where(DocumentChunk.embedding.isnot(None))
        .order_by(distance)
        .limit(settings.rag_top_k)
    )
    result = await db.execute(stmt)
    rows = result.all()

    retrieved = [
        RetrievedChunk(chunk=row[0], document_filename=row[1], score=float(row[2]))
        for row in rows
    ]
    return [item for item in retrieved if item.score >= 0.2]


def build_context_blocks(retrieved: list[RetrievedChunk]) -> list[str]:
    blocks: list[str] = []
    for index, item in enumerate(retrieved, start=1):
        page = item.chunk.page_number
        page_label = f"page {page}" if page is not None else "page unknown"
        document_label = item.document_filename or "unknown document"
        blocks.append(
            f"[Source {index}] ({document_label}, {page_label}): {item.chunk.content}"
        )
    return blocks


def build_history_blocks(messages: list[ChatMessage], limit: int = 4) -> list[str]:
    recent = messages[-limit:] if len(messages) > limit else messages
    blocks: list[str] = []
    for message in recent:
        role = "User" if message.role == MessageRole.USER else "Assistant"
        blocks.append(f"{role}: {message.content}")
    return blocks
