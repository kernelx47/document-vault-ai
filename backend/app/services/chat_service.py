import uuid
from collections.abc import AsyncIterator

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.llm import generate_chat_answer, generate_followup_suggestions, stream_chat_answer
from app.config import get_settings
from app.models import (
    ChatMessage,
    ChatSession,
    ChatSessionDocument,
    Document,
    DocumentStatus,
    MessageRole,
)
from app.schemas.chat import (
    ChatHistoryResponse,
    ChatMessageRequest,
    ChatMessageResponse,
    ChatSessionCreateResponse,
    ChatSessionDetail,
    Citation,
    MultiChatSessionCreateRequest,
)
from app.services.rag_service import generate_rag_answer, prepare_rag_prompt


async def create_chat_session(db: AsyncSession, document_id: uuid.UUID) -> ChatSessionCreateResponse:
    return await create_multi_chat_session(
        db, MultiChatSessionCreateRequest(document_ids=[document_id])
    )


async def create_multi_chat_session(
    db: AsyncSession, payload: MultiChatSessionCreateRequest
) -> ChatSessionCreateResponse:
    settings = get_settings()
    if len(payload.document_ids) > settings.max_multi_doc_chat_documents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Maximum {settings.max_multi_doc_chat_documents} documents per chat session."
            ),
        )

    unique_ids = list(dict.fromkeys(payload.document_ids))
    documents = await _get_ready_documents(db, unique_ids)
    primary = documents[0]

    title = payload.title
    if not title:
        if len(documents) == 1:
            title = f"Chat with {primary.filename}"
        else:
            title = f"Chat across {len(documents)} documents"

    session = ChatSession(document_id=primary.id, title=title)
    db.add(session)
    await db.flush()

    for document in documents:
        db.add(ChatSessionDocument(session_id=session.id, document_id=document.id))

    await db.commit()
    await db.refresh(session)
    return ChatSessionCreateResponse(
        id=session.id,
        document_id=session.document_id,
        document_ids=[document.id for document in documents],
        title=session.title,
        created_at=session.created_at,
    )


async def get_chat_session(db: AsyncSession, session_id: uuid.UUID) -> ChatSessionDetail:
    session = await _get_session_or_raise(db, session_id)
    document_ids = await _get_session_document_ids(db, session)
    message_count = await db.scalar(
        select(func.count()).select_from(ChatMessage).where(ChatMessage.session_id == session.id)
    )
    return ChatSessionDetail(
        id=session.id,
        document_id=session.document_id,
        document_ids=document_ids,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=message_count or 0,
    )


async def ask_question(
    db: AsyncSession, session_id: uuid.UUID, payload: ChatMessageRequest
) -> ChatMessageResponse:
    session, history_messages, question = await _prepare_question(db, session_id, payload)
    document_ids = await _get_session_document_ids(db, session)

    answer, citations, chunk_ids = await generate_rag_answer(
        db,
        document_ids,
        question,
        history_messages,
    )
    followups = generate_followup_suggestions(question, answer)

    assistant_message = await _save_assistant_message(
        db, session, answer, citations, chunk_ids, followups
    )
    session.title = session.title or question[:80]
    await db.commit()
    await db.refresh(assistant_message)

    return _to_message_response(assistant_message, citations, followups)


async def stream_question_answer(
    db: AsyncSession, session_id: uuid.UUID, payload: ChatMessageRequest
) -> AsyncIterator[str]:
    session, history_messages, question = await _prepare_question(db, session_id, payload)
    document_ids = await _get_session_document_ids(db, session)

    _, system_prompt, user_prompt, citations, chunk_ids = await prepare_rag_prompt(
        db, document_ids, question, history_messages
    )

    answer_parts: list[str] = []
    for token in stream_chat_answer(system_prompt, user_prompt):
        answer_parts.append(token)
        yield token

    answer = "".join(answer_parts).strip() or "I don't have enough information in these documents."
    followups = generate_followup_suggestions(question, answer)
    assistant_message = await _save_assistant_message(
        db, session, answer, citations, chunk_ids, followups
    )
    session.title = session.title or question[:80]
    await db.commit()
    await db.refresh(assistant_message)


async def get_chat_history(db: AsyncSession, session_id: uuid.UUID) -> ChatHistoryResponse:
    session = await _get_session_or_raise(db, session_id)
    document_ids = await _get_session_document_ids(db, session)
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.asc())
    )
    messages = result.scalars().all()
    return ChatHistoryResponse(
        session_id=session.id,
        document_id=session.document_id,
        document_ids=document_ids,
        messages=[_to_message_response(message) for message in messages],
    )


async def _prepare_question(
    db: AsyncSession, session_id: uuid.UUID, payload: ChatMessageRequest
) -> tuple[ChatSession, list[ChatMessage], str]:
    session = await _get_session_or_raise(db, session_id)
    document_ids = await _get_session_document_ids(db, session)
    await _get_ready_documents(db, document_ids)

    history_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.asc())
    )
    history_messages = list(history_result.scalars().all())
    question = payload.question.strip()

    user_message = ChatMessage(
        session_id=session.id,
        role=MessageRole.USER,
        content=question,
    )
    db.add(user_message)
    await db.flush()
    return session, history_messages, question


async def _save_assistant_message(
    db: AsyncSession,
    session: ChatSession,
    answer: str,
    citations: list[Citation],
    chunk_ids: list[uuid.UUID],
    followups: list[str],
) -> ChatMessage:
    assistant_message = ChatMessage(
        session_id=session.id,
        role=MessageRole.ASSISTANT,
        content=answer,
        citations=[citation.model_dump(mode="json") for citation in citations],
        retrieved_chunk_ids=[str(chunk_id) for chunk_id in chunk_ids],
        suggested_followups=followups,
    )
    db.add(assistant_message)
    await db.flush()
    return assistant_message


async def _get_ready_documents(db: AsyncSession, document_ids: list[uuid.UUID]) -> list[Document]:
    if not document_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No documents provided.")

    result = await db.execute(select(Document).where(Document.id.in_(document_ids)))
    documents = {document.id: document for document in result.scalars().all()}

    missing = [str(doc_id) for doc_id in document_ids if doc_id not in documents]
    if missing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    not_ready = [str(doc_id) for doc_id in document_ids if documents[doc_id].status != DocumentStatus.READY]
    if not_ready:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="One or more documents are not ready for chat yet.",
        )

    return [documents[doc_id] for doc_id in document_ids]


async def _get_session_document_ids(db: AsyncSession, session: ChatSession) -> list[uuid.UUID]:
    result = await db.execute(
        select(ChatSessionDocument.document_id).where(ChatSessionDocument.session_id == session.id)
    )
    document_ids = [row[0] for row in result.all()]
    if document_ids:
        return document_ids
    return [session.document_id]


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
    message: ChatMessage,
    citations: list[Citation] | None = None,
    followups: list[str] | None = None,
) -> ChatMessageResponse:
    parsed_citations: list[Citation] = []
    if citations is not None:
        parsed_citations = citations
    elif message.citations:
        parsed_citations = [Citation.model_validate(item) for item in message.citations]

    parsed_followups: list[str] = []
    if followups is not None:
        parsed_followups = followups
    elif message.suggested_followups:
        parsed_followups = [str(item) for item in message.suggested_followups]

    return ChatMessageResponse(
        id=message.id,
        role=message.role,
        content=message.content,
        citations=parsed_citations,
        suggested_followups=parsed_followups,
        created_at=message.created_at,
    )
