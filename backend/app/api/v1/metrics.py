from fastapi import APIRouter

router = APIRouter()


@router.get("/documents")
async def document_metrics() -> dict[str, int]:
    return {"total": 0, "ready": 0, "pending": 0, "failed": 0}
