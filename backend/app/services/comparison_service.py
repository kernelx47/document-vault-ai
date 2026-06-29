import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm import compare_documents
from app.models import Document, DocumentStatus
from app.schemas.document_analysis import (
    ComparisonAspect,
    DocumentCompareRequest,
    DocumentCompareResponse,
)


async def compare_document_set(
    db: AsyncSession, payload: DocumentCompareRequest
) -> DocumentCompareResponse:
    unique_ids = list(dict.fromkeys(payload.document_ids))
    result = await db.execute(select(Document).where(Document.id.in_(unique_ids)))
    documents = {document.id: document for document in result.scalars().all()}

    missing = [str(doc_id) for doc_id in unique_ids if doc_id not in documents]
    if missing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    not_ready = [
        str(doc_id)
        for doc_id in unique_ids
        if documents[doc_id].status != DocumentStatus.READY
    ]
    if not_ready:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="One or more documents are not ready for comparison.",
        )

    id_to_label: dict[uuid.UUID, str] = {}
    blocks: list[tuple[str, str]] = []
    for doc_id in unique_ids:
        document = documents[doc_id]
        label = document.filename
        id_to_label[doc_id] = label
        parts = [f"Category: {document.category or 'Unknown'}"]
        if document.tags:
            parts.append(f"Tags: {', '.join(str(tag) for tag in document.tags)}")
        if document.sentiment:
            parts.append(f"Sentiment: {document.sentiment}")
        if document.summary:
            parts.append(f"Summary: {document.summary}")
        if document.insights:
            parts.append("Insights:\n- " + "\n- ".join(str(item) for item in document.insights))
        blocks.append((label, "\n".join(parts)))

    raw = compare_documents(blocks, focus=payload.focus)

    label_to_id = {label: str(doc_id) for doc_id, label in id_to_label.items()}
    table: list[ComparisonAspect] = []
    for row in raw.get("comparison_table", []):
        if not isinstance(row, dict):
            continue
        aspect = str(row.get("aspect", "")).strip()
        values_raw = row.get("values", {})
        if not aspect or not isinstance(values_raw, dict):
            continue
        remapped: dict[str, str] = {}
        for label, value in values_raw.items():
            doc_key = label_to_id.get(str(label), str(label))
            remapped[doc_key] = str(value)
        table.append(ComparisonAspect(aspect=aspect, values=remapped))

    return DocumentCompareResponse(
        summary=str(raw.get("summary", "")).strip(),
        similarities=[str(item) for item in raw.get("similarities", []) if str(item).strip()],
        differences=[str(item) for item in raw.get("differences", []) if str(item).strip()],
        comparison_table=table,
        recommendation=str(raw.get("recommendation")).strip()
        if raw.get("recommendation")
        else None,
        document_filenames={str(doc_id): id_to_label[doc_id] for doc_id in unique_ids},
    )
