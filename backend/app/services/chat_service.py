import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import ChatMessage, ChatSession, Document, DocumentStatus, MessageRole
from app.schemas.chat import (
    ChatHistoryResponse,
    ChatMessageRequest,
    ChatMessageResponse,
    ChatSessionCreateResponse,
    ChatSessionDetail,
    Citation,
)
from app.services.rag_service import generate_rag_answer


async def create_chat_session(db: AsyncSession, document_id: uuid.UUID) -> ChatSessionCreateResponse:
    document = await _get_ready_document(db, document_id)
    session = ChatSession(document_id=document.id, title=f"Chat with {document.filename}")
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return ChatSessionCreateResponse.model_validate(session)


async def get_chat_session(db: AsyncSession, session_id: uuid.UUID) -> ChatSessionDetail:
    session = await _get_session_or_raise(db, session_id)
    message_count = await db.scalar(
        select(func.count()).select_from(ChatMessage).where(ChatMessage.session_id == session.id)
    )
    return ChatSessionDetail(
        id=session.id,
        document_id=session.document_id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=message_count or 0,
    )


async def ask_question(
    db: AsyncSession, session_id: uuid.UUID, payload: ChatMessageRequest
) -> ChatMessageResponse:
    session = await _get_session_or_raise(db, session_id)
    await _get_ready_document(db, session.document_id)

    history_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.asc())
    )
    history_messages = list(history_result.scalars().all())

    user_message = ChatMessage(
        session_id=session.id,
        role=MessageRole.USER,
        content=payload.question.strip(),
    )
    db.add(user_message)
    await db.flush()

    answer, citations, chunk_ids = await generate_rag_answer(
        db,
        session.document_id,
        payload.question.strip(),
        history_messages,
    )

    assistant_message = ChatMessage(
        session_id=session.id,
        role=MessageRole.ASSISTANT,
        content=answer,
        citations=[citation.model_dump(mode="json") for citation in citations],
        retrieved_chunk_ids=[str(chunk_id) for chunk_id in chunk_ids],
    )
    db.add(assistant_message)
    session.title = session.title or payload.question.strip()[:80]
    await db.commit()
    await db.refresh(assistant_message)

    return _to_message_response(assistant_message, citations)


async def get_chat_history(db: AsyncSession, session_id: uuid.UUID) -> ChatHistoryResponse:
    session = await _get_session_or_raise(db, session_id)
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.asc())
    )
    messages = result.scalars().all()
    return ChatHistoryResponse(
        session_id=session.id,
        document_id=session.document_id,
        messages=[_to_message_response(message) for message in messages],
    )


async def _get_ready_document(db: AsyncSession, document_id: uuid.UUID) -> Document:
    document = await db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    if document.status != DocumentStatus.READY:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document is not ready for chat yet.",
        )
    return document


async def _get_session_or_raise(db: AsyncSession, session_id: uuid.UUID) -> ChatSession:
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.id == session_id)
        .options(selectinload(ChatSession.messages))
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found.")
    return session


def _to_message_response(
    message: ChatMessage, citations: list[Citation] | None = None
) -> ChatMessageResponse:
    parsed_citations: list[Citation] = []
    if citations is not None:
        parsed_citations = citations
    elif message.citations:
        parsed_citations = [Citation.model_validate(item) for item in message.citations]

    return ChatMessageResponse(
        id=message.id,
        role=message.role,
        content=message.content,
        citations=parsed_citations,
        created_at=message.created_at,
    )
