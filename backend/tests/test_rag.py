import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.models import Document, DocumentChunk, DocumentStatus
from app.services.rag_service import (
    RetrievedChunk,
    build_context_blocks,
    citations_for_answer,
    extract_cited_source_indices,
    filter_retrieved_by_citations,
    finalize_rag_answer,
    find_invalid_citation_indices,
    retrieve_chunks,
    strip_invalid_citations,
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
    assert retrieved[0].document_filename == "sample.pdf"
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
    provider.embed_query.return_value = [0.0, 1.0] + [0.0] * 382
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
    blocks = build_context_blocks(
        [RetrievedChunk(chunk=chunk, score=0.9, document_filename="policy.pdf")]
    )

    assert len(blocks) == 1
    assert "policy.pdf" in blocks[0]
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
    citations = to_citations(
        [RetrievedChunk(chunk=chunk, score=0.88, document_filename="policy.pdf")]
    )

    assert len(citations) == 1
    assert len(citations[0].excerpt) == 280
    assert citations[0].excerpt.endswith("...")
    assert citations[0].score == 0.88
    assert citations[0].source_index == 1
    assert citations[0].document_filename == "policy.pdf"
    assert citations[0].document_id == chunk.document_id


def test_extract_cited_source_indices_deduplicates_and_preserves_order():
    answer = "Renewal is [Source 2]. Billing is monthly [Source 1]. See again [Source 2]."
    assert extract_cited_source_indices(answer) == [2, 1]


def test_filter_retrieved_by_citations_keeps_only_cited_sources():
    chunks = [
        DocumentChunk(
            id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            chunk_index=index,
            content=f"Chunk {index + 1}",
            page_number=index + 1,
        )
        for index in range(3)
    ]
    retrieved = [RetrievedChunk(chunk=chunk, score=0.9 - index * 0.1, document_filename=f"doc-{index + 1}.pdf") for index, chunk in enumerate(chunks)]
    answer = "The renewal date is December 2025 [Source 1]."

    cited, indices = filter_retrieved_by_citations(retrieved, answer)

    assert len(cited) == 1
    assert cited[0].chunk.id == chunks[0].id
    assert cited[0].document_filename == "doc-1.pdf"


def test_citations_for_answer_ignores_uncited_retrieved_chunks():
    chunks = [
        DocumentChunk(
            id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            chunk_index=index,
            content=f"Chunk {index + 1}",
            page_number=index + 1,
        )
        for index in range(2)
    ]
    retrieved = [RetrievedChunk(chunk=chunk, score=0.9 - index * 0.1, document_filename=f"doc-{index + 1}.pdf") for index, chunk in enumerate(chunks)]
    answer = "Office hours are 9am to 5pm [Source 2]."

    citations, chunk_ids = citations_for_answer(retrieved, answer)

    assert len(citations) == 1
    assert citations[0].source_index == 2
    assert citations[0].page_number == 2
    assert citations[0].document_filename == "doc-2.pdf"
    assert chunk_ids == [chunks[1].id]


def test_citations_for_answer_returns_empty_when_answer_has_no_citations():
    chunks = [
        DocumentChunk(
            id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            chunk_index=0,
            content="Chunk 1",
            page_number=1,
        )
    ]
    retrieved = [RetrievedChunk(chunk=chunks[0], score=0.9)]

    citations, chunk_ids = citations_for_answer(retrieved, "I don't have enough information.")

    assert citations == []
    assert chunk_ids == []


def test_find_invalid_citation_indices_detects_out_of_range_sources():
    answer = "Renewal is December 2025 [Source 1]. Also see [Source 9]."
    assert find_invalid_citation_indices(answer, retrieved_count=2) == [9]


def test_strip_invalid_citations_removes_invalid_and_keeps_valid():
    answer = "Renewal is December 2025 [Source 1]. Also see [Source 9]."
    result = strip_invalid_citations(answer, retrieved_count=2)

    assert result.invalid_indices == [9]
    assert result.answer == "Renewal is December 2025 [Source 1]. Also see."


def test_strip_invalid_citations_removes_all_when_nothing_retrieved():
    result = strip_invalid_citations("Details [Source 1].", retrieved_count=0)

    assert result.invalid_indices == [1]
    assert result.answer == "Details."


def test_finalize_rag_answer_strips_invalid_refs_before_building_citations():
    chunks = [
        DocumentChunk(
            id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            chunk_index=index,
            content=f"Chunk {index + 1}",
            page_number=index + 1,
        )
        for index in range(2)
    ]
    retrieved = [
        RetrievedChunk(chunk=chunk, score=0.9 - index * 0.1, document_filename=f"doc-{index + 1}.pdf")
        for index, chunk in enumerate(chunks)
    ]
    answer = "Renewal is December 2025 [Source 1]. Extra claim [Source 5]."

    cleaned, citations, chunk_ids = finalize_rag_answer(retrieved, answer)

    assert cleaned == "Renewal is December 2025 [Source 1]. Extra claim."
    assert len(citations) == 1
    assert citations[0].source_index == 1
    assert chunk_ids == [chunks[0].id]
