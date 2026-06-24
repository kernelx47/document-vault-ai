from fastapi import APIRouter

router = APIRouter()


@router.get("/sessions")
async def list_sessions() -> dict[str, list]:
    return {"items": []}
