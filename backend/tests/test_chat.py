import uuid
from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.models import ChatMessage, ChatSession, Document, DocumentChunk, DocumentStatus, MessageRole
from app.schemas.chat import ChatMessageRequest
from app.services import chat_service
from app.services.rag_service import RetrievedChunk


@pytest.fixture
async def ready_document(db_session):
    document = Document(
        id=uuid.uuid4(),
        filename="sample.pdf",
        content_type="application/pdf",
        file_path="/tmp/sample.pdf",
        file_size_bytes=100,
        status=DocumentStatus.READY,
        summary="Sample summary",
        chunk_count=1,
    )
    chunk = DocumentChunk(
        id=uuid.uuid4(),
        document_id=document.id,
        chunk_index=0,
        content="The renewal date is December 2025 and billing is monthly.",
        page_number=2,
        embedding=[0.0] * 384,
    )
    db_session.add(document)
    db_session.add(chunk)
    await db_session.commit()
    return document, chunk


@patch("app.services.chat_service.generate_followup_suggestions", return_value=[])
@patch("app.services.rag_service.generate_chat_answer")
@patch("app.services.rag_service.retrieve_chunks")
@pytest.mark.asyncio
async def test_ask_question_returns_answer_with_citations(
    mock_retrieve,
    mock_generate,
    db_session,
    ready_document,
):
    document, chunk = ready_document
    mock_retrieve.return_value = [RetrievedChunk(chunk=chunk, score=0.91)]
    mock_generate.return_value = "The renewal date is December 2025."

    session = await chat_service.create_chat_session(db_session, document.id)
    response = await chat_service.ask_question(
        db_session,
        session.id,
        ChatMessageRequest(question="When is the renewal date?"),
    )

    assert response.role == MessageRole.ASSISTANT
    assert "December 2025" in response.content
    assert len(response.citations) == 1
    assert response.citations[0].page_number == 2


@pytest.mark.asyncio
async def test_create_chat_session(db_session, ready_document):
    document, _ = ready_document
    session = await chat_service.create_chat_session(db_session, document.id)
    assert session.document_id == document.id


@patch("app.services.chat_service.generate_followup_suggestions", return_value=[])
@pytest.mark.asyncio
async def test_chat_history_persists_messages(db_session, ready_document):
    document, chunk = ready_document
    with patch("app.services.rag_service.retrieve_chunks", return_value=[RetrievedChunk(chunk=chunk, score=0.9)]):
        with patch(
            "app.services.rag_service.generate_chat_answer",
            return_value="The renewal date is December 2025.",
        ):
            session = await chat_service.create_chat_session(db_session, document.id)
            await chat_service.ask_question(
                db_session,
                session.id,
                ChatMessageRequest(question="When is the renewal date?"),
            )
            history = await chat_service.get_chat_history(db_session, session.id)

    assert len(history.messages) == 2
    assert history.messages[0].role == MessageRole.USER
    assert history.messages[1].role == MessageRole.ASSISTANT


def test_create_chat_session_api(client):
    from app.db.sync_session import SessionLocal

    document_id = uuid.uuid4()
    session = SessionLocal()
    try:
        document = Document(
            id=document_id,
            filename="sample.pdf",
            content_type="application/pdf",
            file_path="/tmp/sample.pdf",
            file_size_bytes=100,
            status=DocumentStatus.READY,
            chunk_count=0,
        )
        session.add(document)
        session.commit()
    finally:
        session.close()

    response = client.post(f"/api/v1/documents/{document_id}/chat/sessions")
    assert response.status_code == 201
    assert response.json()["document_id"] == str(document_id)

    cleanup = SessionLocal()
    try:
        cleanup.query(ChatMessage).filter(
            ChatMessage.session_id.in_(
                select(ChatSession.id).where(ChatSession.document_id == document_id)
            )
        ).delete(synchronize_session=False)
        cleanup.query(ChatSession).filter(ChatSession.document_id == document_id).delete()
        cleanup.query(Document).filter(Document.id == document_id).delete()
        cleanup.commit()
    finally:
        cleanup.close()
