import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.models import Document, DocumentChunk, DocumentStatus
from app.services.rag_service import (
    RetrievedChunk,
    build_context_blocks,
    retrieve_chunks,
    to_citations,
)


@pytest.fixture
async def document_with_chunks(db_session):
    document = Document(
        id=uuid.uuid4(),
        filename="sample.pdf",
        content_type="application/pdf",
        file_path="/tmp/sample.pdf",
        file_size_bytes=100,
        status=DocumentStatus.READY,
        chunk_count=2,
    )
    chunk_renewal = DocumentChunk(
        id=uuid.uuid4(),
        document_id=document.id,
        chunk_index=0,
        content="The renewal date is December 2025 and billing is monthly.",
        page_number=2,
        embedding=[1.0] + [0.0] * 383,
    )
    chunk_other = DocumentChunk(
        id=uuid.uuid4(),
        document_id=document.id,
        chunk_index=1,
        content="Office hours are 9am to 5pm on weekdays.",
        page_number=3,
        embedding=[0.0] * 384,
    )
    db_session.add(document)
    db_session.add(chunk_renewal)
    db_session.add(chunk_other)
    await db_session.commit()
    return document, chunk_renewal, chunk_other


@patch("app.ai.retrieval.get_embedding_provider")
@pytest.mark.asyncio
async def test_retrieve_chunks_returns_relevant_matches(
    mock_get_provider, db_session, document_with_chunks
):
    document, chunk_renewal, _ = document_with_chunks
    provider = MagicMock()
    provider.embed_query.return_value = [1.0] + [0.0] * 383
    mock_get_provider.return_value = provider

    retrieved = await retrieve_chunks(db_session, [document.id], "When is the renewal date?")

    assert len(retrieved) == 1
    assert retrieved[0].chunk.id == chunk_renewal.id
    assert retrieved[0].score >= 0.2


@patch("app.ai.retrieval.get_embedding_provider")
@pytest.mark.asyncio
async def test_retrieve_chunks_filters_low_similarity(
    mock_get_provider, db_session, document_with_chunks
):
    document, chunk_renewal, chunk_other = document_with_chunks
    chunk_other.embedding = [0.0, 1.0] + [0.0] * 382
    await db_session.commit()

    provider = MagicMock()
    provider.embed_query.return_value = [1.0] + [0.0] * 383
    mock_get_provider.return_value = provider

    retrieved = await retrieve_chunks(db_session, [document.id], "Unrelated question")

    assert all(item.chunk.id != chunk_renewal.id for item in retrieved)
    assert all(item.score >= 0.2 for item in retrieved)


def test_build_context_blocks_includes_page_numbers():
    chunk = DocumentChunk(
        id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        chunk_index=0,
        content="Renewal date December 2025.",
        page_number=2,
    )
    blocks = build_context_blocks([RetrievedChunk(chunk=chunk, score=0.9)])

    assert len(blocks) == 1
    assert "page 2" in blocks[0]
    assert "Renewal date December 2025." in blocks[0]


def test_to_citations_truncates_long_excerpts():
    long_text = "x" * 300
    chunk = DocumentChunk(
        id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        chunk_index=0,
        content=long_text,
        page_number=1,
    )
    citations = to_citations([RetrievedChunk(chunk=chunk, score=0.88)])

    assert len(citations) == 1
    assert len(citations[0].excerpt) == 280
    assert citations[0].excerpt.endswith("...")
    assert citations[0].score == 0.88
