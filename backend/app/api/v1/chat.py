import json
from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.chat import (
    ChatHistoryResponse,
    ChatMessageRequest,
    ChatMessageResponse,
    ChatSessionCreateResponse,
    ChatSessionDetail,
    MultiChatSessionCreateRequest,
)
from app.services import chat_service

router = APIRouter()


@router.post(
    "/sessions",
    status_code=status.HTTP_201_CREATED,
    response_model=ChatSessionCreateResponse,
    summary="Start a multi-document chat session",
    description="Create a chat session spanning one or more ready documents.",
)
async def create_multi_chat_session(
    payload: MultiChatSessionCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> ChatSessionCreateResponse:
    return await chat_service.create_multi_chat_session(db, payload)


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
    summary="Ask a question",
    description="Run RAG over the session documents and return an assistant message with citations.",
)
async def send_chat_message(
    session_id: UUID,
    payload: ChatMessageRequest,
    db: AsyncSession = Depends(get_db),
) -> ChatMessageResponse:
    return await chat_service.ask_question(db, session_id, payload)


@router.post(
    "/sessions/{session_id}/messages/stream",
    summary="Ask a question with streaming response",
    description="Stream the assistant answer as Server-Sent Events (SSE).",
)
async def stream_chat_message(
    session_id: UUID,
    payload: ChatMessageRequest,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    async def event_stream() -> AsyncIterator[str]:
        async for token in chat_service.stream_question_answer(db, session_id, payload):
            yield f"data: {json.dumps({'token': token})}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/sessions/{session_id}/messages", response_model=ChatHistoryResponse)
async def get_chat_messages(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ChatHistoryResponse:
    return await chat_service.get_chat_history(db, session_id)
