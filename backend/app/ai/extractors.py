"""Document text extraction for PDF and DOCX file formats."""

import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("app.extractors")


@dataclass
class TextSegment:
    """A contiguous block of text extracted from a document page or section."""

    text: str
    page_number: int | None = None


def extract_text(file_path: str, content_type: str) -> tuple[list[TextSegment], int]:
    """Dispatch extraction to the appropriate handler based on MIME type."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Document file not found: {path.name}")

    if content_type == "application/pdf":
        return _extract_pdf(file_path)
    if content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return _extract_docx(file_path)
    raise ValueError(f"Unsupported content type: {content_type}")


def _extract_pdf(file_path: str) -> tuple[list[TextSegment], int]:
    import pdfplumber

    try:
        segments: list[TextSegment] = []
        with pdfplumber.open(file_path) as pdf:
            page_count = len(pdf.pages)
            for index, page in enumerate(pdf.pages, start=1):
                text = (page.extract_text() or "").strip()
                if text:
                    segments.append(TextSegment(text=text, page_number=index))
        return segments, page_count
    except Exception as exc:
        raise ValueError(f"Failed to extract text from PDF: {type(exc).__name__}") from exc


def _extract_docx(file_path: str) -> tuple[list[TextSegment], int]:
    from docx import Document

    try:
        doc = Document(file_path)
        paragraphs = [paragraph.text.strip() for paragraph in doc.paragraphs if paragraph.text.strip()]
        full_text = "\n".join(paragraphs)
        segments = [TextSegment(text=full_text, page_number=None)] if full_text else []
        return segments, 1
    except Exception as exc:
        raise ValueError(f"Failed to extract text from DOCX: {type(exc).__name__}") from exc
