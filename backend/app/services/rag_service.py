import logging
import re
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.langchain_rag import contextualize_question, generate_answer, stream_answer
from app.ai.retrieval import (
    RetrievedChunk,
    build_context_blocks,
    build_history_blocks,
    retrieve_chunks,
)
from app.models import ChatMessage
from app.schemas.chat import Citation

logger = logging.getLogger("app.rag")

_SOURCE_CITATION_RE = re.compile(r"\[Source\s+(\d+)\]", re.IGNORECASE)

__all__ = [
    "RetrievedChunk",
    "build_context_blocks",
    "build_history_blocks",
    "retrieve_chunks",
    "retrieve_for_question",
    "generate_rag_answer",
    "prepare_rag_prompt",
    "to_citations",
    "extract_cited_source_indices",
    "find_invalid_citation_indices",
    "strip_invalid_citations",
    "finalize_rag_answer",
    "citations_for_answer",
]


@dataclass(frozen=True)
class CitationValidationResult:
    answer: str
    invalid_indices: list[int]


async def retrieve_for_question(
    db: AsyncSession,
    document_ids: list[UUID],
    question: str,
    history_messages: list[ChatMessage],
) -> list[RetrievedChunk]:
    """Retrieve chunks once, using history-aware query rewriting when needed."""
    search_query = await contextualize_question(question, history_messages)
    return await retrieve_chunks(db, document_ids, search_query)


def extract_cited_source_indices(answer: str) -> list[int]:
    """Return unique [Source N] indices in order of first appearance."""
    seen: set[int] = set()
    indices: list[int] = []
    for match in _SOURCE_CITATION_RE.finditer(answer):
        index = int(match.group(1))
        if index not in seen:
            seen.add(index)
            indices.append(index)
    return indices


def filter_retrieved_by_citations(
    retrieved: list[RetrievedChunk],
    answer: str,
) -> tuple[list[RetrievedChunk], list[int]]:
    """Keep only retrieved chunks referenced as [Source N] in the answer."""
    indices = extract_cited_source_indices(answer)
    if not indices:
        return [], []

    cited_chunks: list[RetrievedChunk] = []
    cited_indices: list[int] = []
    for index in indices:
        position = index - 1
        if 0 <= position < len(retrieved):
            cited_chunks.append(retrieved[position])
            cited_indices.append(index)
    return cited_chunks, cited_indices


def to_citations(
    retrieved: list[RetrievedChunk],
    *,
    source_indices: list[int] | None = None,
) -> list[Citation]:
    citations: list[Citation] = []
    for position, item in enumerate(retrieved):
        excerpt = item.chunk.content
        if len(excerpt) > 280:
            excerpt = excerpt[:277] + "..."
        source_index = (
            source_indices[position]
            if source_indices is not None
            else position + 1
        )
        citations.append(
            Citation(
                chunk_id=item.chunk.id,
                document_id=item.chunk.document_id,
                document_filename=item.document_filename,
                page_number=item.chunk.page_number,
                excerpt=excerpt,
                score=round(item.score, 4),
                source_index=source_index,
            )
        )
    return citations


def citations_for_answer(
    retrieved: list[RetrievedChunk],
    answer: str,
) -> tuple[list[Citation], list[UUID]]:
    """Build citations and chunk IDs only for sources cited in the answer."""
    cited_chunks, cited_indices = filter_retrieved_by_citations(retrieved, answer)
    citations = to_citations(cited_chunks, source_indices=cited_indices)
    chunk_ids = [item.chunk.id for item in cited_chunks]
    return citations, chunk_ids


def find_invalid_citation_indices(answer: str, retrieved_count: int) -> list[int]:
    """Return unique [Source N] indices that do not map to retrieved context."""
    invalid: list[int] = []
    seen: set[int] = set()
    for match in _SOURCE_CITATION_RE.finditer(answer):
        index = int(match.group(1))
        if index in seen:
            continue
        seen.add(index)
        if index < 1 or index > retrieved_count:
            invalid.append(index)
    return invalid


def strip_invalid_citations(answer: str, retrieved_count: int) -> CitationValidationResult:
    """Remove [Source N] markers that reference chunks outside retrieved context."""
    invalid_indices: list[int] = []
    seen_invalid: set[int] = set()

    def replacer(match: re.Match[str]) -> str:
        index = int(match.group(1))
        if 1 <= index <= retrieved_count:
            return match.group(0)
        if index not in seen_invalid:
            seen_invalid.add(index)
            invalid_indices.append(index)
        return ""

    cleaned = _SOURCE_CITATION_RE.sub(replacer, answer)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r" ([,.;:!?])", r"\1", cleaned)
    return CitationValidationResult(answer=cleaned.strip(), invalid_indices=invalid_indices)


def finalize_rag_answer(
    retrieved: list[RetrievedChunk],
    answer: str,
) -> tuple[str, list[Citation], list[UUID]]:
    """Validate inline citations, strip invalid refs, and build citation metadata."""
    validation = strip_invalid_citations(answer, len(retrieved))
    if validation.invalid_indices:
        logger.warning(
            "Stripped invalid citation indices %s (retrieved_count=%d)",
            validation.invalid_indices,
            len(retrieved),
        )
    citations, chunk_ids = citations_for_answer(retrieved, validation.answer)
    return validation.answer, citations, chunk_ids


async def generate_rag_answer(
    db: AsyncSession,
    document_ids: list[UUID],
    question: str,
    history_messages: list[ChatMessage],
    *,
    retrieved: list[RetrievedChunk] | None = None,
) -> tuple[str, list[Citation], list[UUID]]:
    chunks = retrieved
    if chunks is None:
        chunks = await retrieve_for_question(db, document_ids, question, history_messages)
    answer = await generate_answer(question, history_messages, chunks)
    return finalize_rag_answer(chunks, answer)


async def prepare_rag_prompt(
    db: AsyncSession,
    document_ids: list[UUID],
    question: str,
    history_messages: list[ChatMessage],
) -> tuple[list[RetrievedChunk], str, str, list[Citation], list[UUID]]:
    from app.ai.prompts import build_chat_prompt

    retrieved = await retrieve_for_question(db, document_ids, question, history_messages)
    context_blocks = build_context_blocks(retrieved)
    history_blocks = build_history_blocks(history_messages)
    system_prompt, user_prompt = build_chat_prompt(question, context_blocks, history_blocks)
    citations = to_citations(retrieved)
    chunk_ids = [item.chunk.id for item in retrieved]
    return retrieved, system_prompt, user_prompt, citations, chunk_ids
