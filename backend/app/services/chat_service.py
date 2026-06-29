"""Chat session and message orchestration — creates sessions, runs RAG, persists history."""

import logging
import re
import time
import uuid
from collections.abc import AsyncIterator

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.guardrails import InputBlockedError, check_input_async, check_output_async
from app.ai.langchain_rag import stream_answer as langchain_stream_answer
from app.ai.llm import generate_followup_suggestions, generate_session_title
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
from app.services.rag_service import finalize_rag_answer, generate_rag_answer, retrieve_for_question
from app.services.rag_metrics import record_chat_request

logger = logging.getLogger("app.chat")

_AUTO_TITLE_PREFIXES = ("Chat with ", "Chat across ")
_TRIVIAL_GREETING = re.compile(
    r"^(?:hi|hello|hey|thanks|thank you|ok|okay|yo|good morning|good afternoon|good evening)[\s!.?,]*$",
    re.IGNORECASE,
)


async def create_chat_session(db: AsyncSession, document_id: uuid.UUID) -> ChatSessionCreateResponse:
    """Create a chat session for a single document."""
    return await create_multi_chat_session(
        db, MultiChatSessionCreateRequest(document_ids=[document_id])
    )


async def create_multi_chat_session(
    db: AsyncSession, payload: MultiChatSessionCreateRequest
) -> ChatSessionCreateResponse:
    """Create a chat session spanning multiple documents."""
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
        title = None

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
    """Return session metadata including linked documents and message count."""
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
    """Run RAG pipeline and return an answer with citations."""
    session, history_messages, question = await _prepare_question(db, session_id, payload)
    document_ids = await _get_session_document_ids(db, session)
    started = time.perf_counter()
    retrieval_ms: float | None = None
    success = False

    try:
        retrieve_started = time.perf_counter()
        retrieved = await retrieve_for_question(db, document_ids, question, history_messages)
        retrieval_ms = round((time.perf_counter() - retrieve_started) * 1000, 2)
        answer, citations, chunk_ids = await generate_rag_answer(
            db,
            document_ids,
            question,
            history_messages,
            retrieved=retrieved,
        )
        success = True
    except Exception:
        logger.exception("RAG answer generation failed for session %s", session_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to generate answer. Please try again.",
        )
    finally:
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        try:
            await record_chat_request(
                duration_ms=duration_ms,
                retrieval_ms=retrieval_ms,
                success=success,
            )
        except Exception:
            logger.debug("Failed to record chat metrics", exc_info=True)

    answer = await check_output_async(answer)

    document_context, citation_context = await _build_followup_context(db, document_ids, citations)
    try:
        followups = generate_followup_suggestions(
            question,
            answer,
            document_context=document_context,
            citation_context=citation_context,
            has_citations=bool(citations),
        )
    except Exception:
        logger.debug("Followup generation failed — continuing without suggestions", exc_info=True)
        followups = []

    assistant_message = await _save_assistant_message(
        db, session, answer, citations, chunk_ids, followups
    )
    await _maybe_update_session_title(session, history_messages, question, answer)
    await db.commit()
    await db.refresh(assistant_message)

    return _to_message_response(assistant_message, citations, followups)


async def stream_question_answer(
    db: AsyncSession, session_id: uuid.UUID, payload: ChatMessageRequest
) -> AsyncIterator[str]:
    """Stream RAG answer tokens via server-sent events."""
    session, history_messages, question = await _prepare_question(db, session_id, payload)
    document_ids = await _get_session_document_ids(db, session)
    started = time.perf_counter()
    retrieval_ms: float | None = None
    success = False

    try:
        retrieve_started = time.perf_counter()
        retrieved = await retrieve_for_question(db, document_ids, question, history_messages)
        retrieval_ms = round((time.perf_counter() - retrieve_started) * 1000, 2)

        answer_parts: list[str] = []
        async for token in langchain_stream_answer(question, history_messages, retrieved):
            answer_parts.append(token)
            yield token

        answer = "".join(answer_parts).strip() or "I don't have enough information in these documents."
        answer, citations, chunk_ids = finalize_rag_answer(retrieved, answer)
        answer = await check_output_async(answer)
        document_context, citation_context = await _build_followup_context(db, document_ids, citations)
        try:
            followups = generate_followup_suggestions(
                question,
                answer,
                document_context=document_context,
                citation_context=citation_context,
                has_citations=bool(citations),
            )
        except Exception:
            logger.debug("Followup generation failed during stream — continuing without suggestions", exc_info=True)
            followups = []
        assistant_message = await _save_assistant_message(
            db, session, answer, citations, chunk_ids, followups
        )
        await _maybe_update_session_title(session, history_messages, question, answer)
        await db.commit()
        await db.refresh(assistant_message)
        success = True
    finally:
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        try:
            await record_chat_request(
                duration_ms=duration_ms,
                retrieval_ms=retrieval_ms,
                success=success,
            )
        except Exception:
            logger.debug("Failed to record chat metrics", exc_info=True)


async def get_chat_history(db: AsyncSession, session_id: uuid.UUID) -> ChatHistoryResponse:
    """Return all messages in a chat session, oldest first."""
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
        title=session.title,
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
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty or whitespace-only.",
        )

    try:
        await check_input_async(question)
    except InputBlockedError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.reason,
        ) from exc

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


async def _build_followup_context(
    db: AsyncSession,
    document_ids: list[uuid.UUID],
    citations: list[Citation],
) -> tuple[str, str]:
    result = await db.execute(select(Document).where(Document.id.in_(document_ids)))
    documents = result.scalars().all()
    doc_lines: list[str] = []
    for document in documents:
        tag_text = ", ".join(str(tag) for tag in (document.tags or []))
        line = (
            f"- {document.filename} ({document.category or 'Uncategorized'}, "
            f"sentiment: {document.sentiment or 'unknown'}"
        )
        if tag_text:
            line += f", tags: {tag_text}"
        if document.summary:
            line += f"): {document.summary[:240]}"
        else:
            line += ")"
        doc_lines.append(line)

    document_context = "\n".join(doc_lines) if doc_lines else "No document metadata available."
    citation_lines = [
        f"- [Source {citation.source_index}] {citation.document_filename or 'document'}: "
        f"{citation.excerpt[:160]}"
        for citation in citations[:5]
        if citation.source_index is not None
    ]
    citation_context = (
        "\n".join(citation_lines) if citation_lines else "No citations in the last answer."
    )
    return document_context, citation_context


_WEAK_TITLE = re.compile(
    r"^(?:hi|hello|hey|thanks|thank you|ok|okay|yo|greeting|new chat|chat|help)[\s!.?,:-]*$",
    re.IGNORECASE,
)


def _needs_generated_title(title: str | None) -> bool:
    if not title:
        return True
    if title.startswith(_AUTO_TITLE_PREFIXES):
        return True
    if _is_weak_title(title):
        return True
    return False


def _is_trivial_greeting(text: str) -> bool:
    return bool(_TRIVIAL_GREETING.match(text.strip()))


def _is_weak_title(title: str) -> bool:
    return bool(_WEAK_TITLE.match(title.strip()))


def _fallback_title_from_answer(answer: str) -> str | None:
    text = answer.strip()
    if len(text) < 24:
        return None
    sentence = re.split(r"[.!?\n]", text, maxsplit=1)[0].strip()
    if len(sentence) < 12 or _is_weak_title(sentence):
        return None
    if len(sentence) <= 60:
        return sentence
    return sentence[:57] + "..."


def _sanitize_generated_title(
    title: str,
    *,
    question: str,
    all_user_messages: list[str],
) -> str | None:
    cleaned = title.strip()
    if not cleaned or _is_weak_title(cleaned):
        return None
    if cleaned.lower() == question.strip().lower():
        return None
    if len(all_user_messages) == 1 and cleaned.lower() == all_user_messages[0].strip().lower():
        return None
    return cleaned


def _format_conversation_for_title(
    history_messages: list[ChatMessage],
    question: str,
    answer: str,
) -> str:
    lines: list[str] = []
    for message in history_messages:
        role = "User" if message.role == MessageRole.USER else "Assistant"
        lines.append(f"{role}: {message.content[:500]}")
    lines.append(f"User: {question[:500]}")
    lines.append(f"Assistant: {answer[:500]}")
    return "\n".join(lines)


async def _maybe_update_session_title(
    session: ChatSession,
    history_messages: list[ChatMessage],
    question: str,
    answer: str,
) -> None:
    if not _needs_generated_title(session.title):
        return

    prior_user_messages = [message.content for message in history_messages if message.role == MessageRole.USER]
    all_user_messages = prior_user_messages + [question]
    if len(all_user_messages) == 1 and _is_trivial_greeting(all_user_messages[0]):
        return

    conversation = _format_conversation_for_title(history_messages, question, answer)
    title: str | None = None
    try:
        title = generate_session_title(conversation)
    except Exception:
        logger.debug("Session title generation failed", exc_info=True)

    if title:
        title = _sanitize_generated_title(
            title,
            question=question,
            all_user_messages=all_user_messages,
        )

    if not title:
        title = _fallback_title_from_answer(answer)

    if not title:
        return

    session.title = title[:512]


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
        for item in message.citations:
            try:
                parsed_citations.append(Citation.model_validate(item))
            except (ValidationError, Exception):
                logger.debug("Skipping corrupt citation data: %s", item)

    parsed_followups: list[str] = []
    if followups is not None:
        parsed_followups = followups
    elif message.suggested_followups:
        parsed_followups = [str(item) for item in message.suggested_followups]

    parsed_chunk_ids: list[uuid.UUID] = []
    if message.retrieved_chunk_ids:
        for chunk_id in message.retrieved_chunk_ids:
            try:
                parsed_chunk_ids.append(uuid.UUID(str(chunk_id)))
            except ValueError:
                logger.debug("Skipping invalid retrieved_chunk_id: %s", chunk_id)

    return ChatMessageResponse(
        id=message.id,
        role=message.role,
        content=message.content,
        citations=parsed_citations,
        retrieved_chunk_ids=parsed_chunk_ids,
        suggested_followups=parsed_followups,
        created_at=message.created_at,
    )
