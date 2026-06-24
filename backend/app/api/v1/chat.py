from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.chat import (
    ChatHistoryResponse,
    ChatMessageRequest,
    ChatMessageResponse,
    ChatSessionDetail,
)
from app.services import chat_service

router = APIRouter()


@router.get("/sessions/{session_id}", response_model=ChatSessionDetail)
async def get_chat_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ChatSessionDetail:
    return await chat_service.get_chat_session(db, session_id)


@router.post(
    "/sessions/{session_id}/messages",
    status_code=status.HTTP_200_OK,
    response_model=ChatMessageResponse,
)
async def send_chat_message(
    session_id: UUID,
    payload: ChatMessageRequest,
    db: AsyncSession = Depends(get_db),
) -> ChatMessageResponse:
    return await chat_service.ask_question(db, session_id, payload)


@router.get("/sessions/{session_id}/messages", response_model=ChatHistoryResponse)
async def get_chat_messages(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ChatHistoryResponse:
    return await chat_service.get_chat_history(db, session_id)
