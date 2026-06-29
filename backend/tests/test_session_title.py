import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.models import ChatMessage, ChatSession, Document, DocumentChunk, DocumentStatus, MessageRole
from app.schemas.chat import ChatMessageRequest, MultiChatSessionCreateRequest
from app.services import chat_service
from app.services.rag_service import RetrievedChunk


@pytest.fixture
async def ready_document(db_session):
    document = Document(
        id=uuid.uuid4(),
        filename="policy.pdf",
        content_type="application/pdf",
        file_path="/tmp/policy.pdf",
        file_size_bytes=100,
        status=DocumentStatus.READY,
        chunk_count=1,
    )
    chunk = DocumentChunk(
        id=uuid.uuid4(),
        document_id=document.id,
        chunk_index=0,
        content="Renewal date December 2025.",
        page_number=1,
        embedding=[1.0] + [0.0] * 383,
    )
    db_session.add(document)
    db_session.add(chunk)
    await db_session.commit()
    return document


@pytest.mark.asyncio
async def test_trivial_greeting_defers_title(db_session, ready_document):
    session = await chat_service.create_multi_chat_session(
        db_session,
        MultiChatSessionCreateRequest(document_ids=[ready_document.id]),
    )

    with (
        patch("app.services.chat_service.retrieve_for_question", new_callable=AsyncMock, return_value=[]),
        patch("app.services.rag_service.generate_answer", new_callable=AsyncMock, return_value="Hello! How can I help?"),
        patch("app.services.chat_service.generate_followup_suggestions", return_value=[]),
    ):
        await chat_service.ask_question(
            db_session,
            session.id,
            ChatMessageRequest(question="hello"),
        )

    result = await db_session.get(ChatSession, session.id)
    assert result is not None
    assert result.title is None


@pytest.mark.asyncio
async def test_substantive_question_generates_title(db_session, ready_document):
    session = await chat_service.create_multi_chat_session(
        db_session,
        MultiChatSessionCreateRequest(document_ids=[ready_document.id]),
    )

    with (
        patch("app.services.chat_service.retrieve_for_question", new_callable=AsyncMock) as mock_retrieve,
        patch("app.services.rag_service.generate_answer", new_callable=AsyncMock, return_value="Renewal is December 2025 [Source 1]."),
        patch("app.services.chat_service.generate_followup_suggestions", return_value=[]),
        patch("app.services.chat_service.generate_session_title", return_value="Policy Renewal Date"),
    ):
        mock_retrieve.return_value = [
            RetrievedChunk(
                chunk=DocumentChunk(
                    id=uuid.uuid4(),
                    document_id=ready_document.id,
                    chunk_index=0,
                    content="Renewal date December 2025.",
                    page_number=1,
                    embedding=[1.0] + [0.0] * 383,
                ),
                score=0.9,
            )
        ]
        await chat_service.ask_question(
            db_session,
            session.id,
            ChatMessageRequest(question="When is renewal?"),
        )

    result = await db_session.get(ChatSession, session.id)
    assert result is not None
    assert result.title == "Policy Renewal Date"


@pytest.mark.asyncio
async def test_title_generated_after_greeting_follow_up(db_session, ready_document):
    session = await chat_service.create_multi_chat_session(
        db_session,
        MultiChatSessionCreateRequest(document_ids=[ready_document.id]),
    )

    with (
        patch("app.services.chat_service.retrieve_for_question", new_callable=AsyncMock, return_value=[]),
        patch("app.services.rag_service.generate_answer", new_callable=AsyncMock, return_value="Hello! Ask me about your documents."),
        patch("app.services.chat_service.generate_followup_suggestions", return_value=[]),
    ):
        await chat_service.ask_question(
            db_session,
            session.id,
            ChatMessageRequest(question="hi"),
        )

    with (
        patch("app.services.chat_service.retrieve_for_question", new_callable=AsyncMock) as mock_retrieve,
        patch("app.services.rag_service.generate_answer", new_callable=AsyncMock, return_value="The GL limit is $2M per occurrence [Source 1]."),
        patch("app.services.chat_service.generate_followup_suggestions", return_value=[]),
        patch("app.services.chat_service.generate_session_title", return_value="GL Coverage Limits"),
    ):
        mock_retrieve.return_value = [
            RetrievedChunk(
                chunk=DocumentChunk(
                    id=uuid.uuid4(),
                    document_id=ready_document.id,
                    chunk_index=0,
                    content="GL limit is $2M per occurrence.",
                    page_number=1,
                    embedding=[1.0] + [0.0] * 383,
                ),
                score=0.9,
            )
        ]
        await chat_service.ask_question(
            db_session,
            session.id,
            ChatMessageRequest(question="What is the GL limit?"),
        )

    result = await db_session.get(ChatSession, session.id)
    assert result is not None
    assert result.title == "GL Coverage Limits"


def test_format_conversation_for_title():
    history = [
        ChatMessage(
            session_id=uuid.uuid4(),
            role=MessageRole.USER,
            content="hi",
        ),
        ChatMessage(
            session_id=uuid.uuid4(),
            role=MessageRole.ASSISTANT,
            content="Hello!",
        ),
    ]
    text = chat_service._format_conversation_for_title(
        history,
        "What is the GL limit?",
        "The GL limit is $2M.",
    )
    assert "User: hi" in text
    assert "User: What is the GL limit?" in text
    assert "Assistant: The GL limit is $2M." in text
