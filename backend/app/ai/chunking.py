"""Split extracted text segments into overlapping fixed-size chunks for embedding."""

from dataclasses import dataclass

from app.ai.extractors import TextSegment
from app.config import get_settings


@dataclass
class TextChunk:
    """A single text chunk with positional metadata for vector storage."""

    content: str
    page_number: int | None
    chunk_index: int


def chunk_segments(segments: list[TextSegment]) -> list[TextChunk]:
    """Partition text segments into overlapping chunks using configured size and overlap."""
    settings = get_settings()
    chunk_size = settings.chunk_size
    overlap = settings.chunk_overlap

    chunks: list[TextChunk] = []
    chunk_index = 0

    for segment in segments:
        text = segment.text
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            content = text[start:end].strip()
            if content:
                chunks.append(
                    TextChunk(
                        content=content,
                        page_number=segment.page_number,
                        chunk_index=chunk_index,
                    )
                )
                chunk_index += 1
            if end >= len(text):
                break
            start = max(end - overlap, start + 1)

    return chunks
