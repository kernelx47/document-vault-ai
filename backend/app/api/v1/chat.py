"""Chat session and messaging endpoints with RAG and streaming support."""

import json
import logging
from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
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
from app.schemas.openapi_examples import (
    CHAT_MESSAGE_REQUEST_EXAMPLE,
    CHAT_STREAM_SSE_EXAMPLE,
    MULTI_CHAT_SESSION_REQUEST_EXAMPLE,
)
from app.schemas.openapi_responses import (
    CHAT_MESSAGE_RESPONSES,
    CHAT_SESSION_RESPONSES,
    RESPONSE_422,
    merge_responses,
)
from app.services import chat_service
from app.services.rate_limit_service import enforce_chat_rate_limit, enforce_daily_ai_quota

router = APIRouter()
logger = logging.getLogger("app.api.chat")


@router.post(
    "/sessions",
    status_code=status.HTTP_201_CREATED,
    response_model=ChatSessionCreateResponse,
    summary="Start a multi-document chat session",
    response_description="New chat session spanning one or more ready documents.",
    description=(
        "Create a chat session across multiple documents. "
        "All `document_ids` must exist and be in `ready` status."
    ),
    responses=CHAT_SESSION_RESPONSES,
)
async def create_multi_chat_session(
    payload: MultiChatSessionCreateRequest = Body(
        openapi_examples={"compare_policies": {"summary": "Compare two policies", "value": MULTI_CHAT_SESSION_REQUEST_EXAMPLE}},
    ),
    db: AsyncSession = Depends(get_db),
) -> ChatSessionCreateResponse:
    return await chat_service.create_multi_chat_session(db, payload)


@router.get(
    "/sessions/{session_id}",
    response_model=ChatSessionDetail,
    summary="Get chat session",
    response_description="Session metadata including linked documents and message count.",
    description="Returns session details and the number of messages exchanged so far.",
    responses=CHAT_SESSION_RESPONSES,
)
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
    response_description="Assistant answer with citations from retrieved document chunks.",
    description=(
        "Run RAG over the session documents and return an assistant message with citations. "
        "The question is persisted; use `GET /chat/sessions/{id}/messages` for full history."
    ),
    responses=merge_responses(CHAT_MESSAGE_RESPONSES, RESPONSE_422),
)
async def send_chat_message(
    request: Request,
    session_id: UUID,
    payload: ChatMessageRequest = Body(
        openapi_examples={
            "renewal_date": {"summary": "Ask about renewal date", "value": CHAT_MESSAGE_REQUEST_EXAMPLE},
            "coverage_limits": {"summary": "Ask about coverage", "value": {"question": "What are the coverage limits?"}},
            "summary": {"summary": "Ask for a summary", "value": {"question": "Summarize this document in 3 bullet points."}},
        },
    ),
    db: AsyncSession = Depends(get_db),
) -> ChatMessageResponse:
    client_ip = request.client.host if request.client else "unknown"
    await enforce_chat_rate_limit(client_ip)
    await enforce_daily_ai_quota()
    return await chat_service.ask_question(db, session_id, payload)


@router.post(
    "/sessions/{session_id}/messages/stream",
    summary="Ask a question (streaming)",
    response_description="Server-Sent Events stream of answer tokens.",
    description=(
        "Stream the assistant answer as Server-Sent Events (SSE). "
        "Each event is JSON: `{\"token\": \"...\"}` until `{\"done\": true}`. "
        "Errors are sent as `{\"error\": \"...\"}` events."
    ),
    responses=merge_responses(
        CHAT_MESSAGE_RESPONSES,
        RESPONSE_422,
        {
            200: {
                "description": "SSE stream of JSON token events",
                "content": {
                    "text/event-stream": {
                        "example": CHAT_STREAM_SSE_EXAMPLE,
                    }
                },
            }
        },
    ),
)
async def stream_chat_message(
    request: Request,
    session_id: UUID,
    payload: ChatMessageRequest = Body(
        openapi_examples={
            "renewal_date": {"summary": "Ask about renewal date", "value": CHAT_MESSAGE_REQUEST_EXAMPLE},
            "coverage_limits": {"summary": "Ask about coverage", "value": {"question": "What are the coverage limits?"}},
        },
    ),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    client_ip = request.client.host if request.client else "unknown"
    await enforce_chat_rate_limit(client_ip)
    await enforce_daily_ai_quota()

    async def event_stream() -> AsyncIterator[str]:
        try:
            async for token in chat_service.stream_question_answer(db, session_id, payload):
                yield f"data: {json.dumps({'token': token})}\n\n"
            history = await chat_service.get_chat_history(db, session_id)
            last_msg = history.messages[-1] if history.messages else None
            done_payload: dict = {"done": True, "title": history.title}
            if last_msg and last_msg.role == "assistant":
                done_payload["suggested_followups"] = last_msg.suggested_followups
                done_payload["citations"] = [c.model_dump(mode="json") for c in last_msg.citations]
            yield f"data: {json.dumps(done_payload, default=str)}\n\n"
        except HTTPException as exc:
            yield f"data: {json.dumps({'error': exc.detail})}\n\n"
        except Exception:
            logger.exception("Streaming error for session %s", session_id)
            yield f"data: {json.dumps({'error': 'An error occurred while generating the response.'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get(
    "/sessions/{session_id}/messages",
    response_model=ChatHistoryResponse,
    summary="Get chat history",
    response_description="All messages in the session, oldest first.",
    description="Returns the full conversation history including citations on assistant messages.",
    responses=CHAT_SESSION_RESPONSES,
)
async def get_chat_messages(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ChatHistoryResponse:
    return await chat_service.get_chat_history(db, session_id)
