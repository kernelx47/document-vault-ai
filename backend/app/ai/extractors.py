from dataclasses import dataclass


@dataclass
class TextSegment:
    text: str
    page_number: int | None = None


def extract_text(file_path: str, content_type: str) -> tuple[list[TextSegment], int]:
    if content_type == "application/pdf":
        return _extract_pdf(file_path)
    if content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return _extract_docx(file_path)
    raise ValueError(f"Unsupported content type: {content_type}")


def _extract_pdf(file_path: str) -> tuple[list[TextSegment], int]:
    import pdfplumber

    segments: list[TextSegment] = []
    with pdfplumber.open(file_path) as pdf:
        page_count = len(pdf.pages)
        for index, page in enumerate(pdf.pages, start=1):
            text = (page.extract_text() or "").strip()
            if text:
                segments.append(TextSegment(text=text, page_number=index))
    return segments, page_count


def _extract_docx(file_path: str) -> tuple[list[TextSegment], int]:
    from docx import Document

    doc = Document(file_path)
    paragraphs = [paragraph.text.strip() for paragraph in doc.paragraphs if paragraph.text.strip()]
    full_text = "\n".join(paragraphs)
    segments = [TextSegment(text=full_text, page_number=None)] if full_text else []
    return segments, 1
