import json
import uuid
from unittest.mock import patch

import pytest

from app.models import ChatSessionDocument, Document, DocumentChunk, DocumentStatus
from app.schemas.chat import ChatMessageRequest, MultiChatSessionCreateRequest
from app.services import chat_service
from app.services.rag_service import RetrievedChunk


@pytest.fixture
async def two_ready_documents(db_session):
    documents = []
    for index, name in enumerate(["alpha.pdf", "beta.pdf"], start=1):
        document = Document(
            id=uuid.uuid4(),
            filename=name,
            content_type="application/pdf",
            file_path=f"/tmp/{name}",
            file_size_bytes=100,
            status=DocumentStatus.READY,
            chunk_count=1,
        )
        chunk = DocumentChunk(
            id=uuid.uuid4(),
            document_id=document.id,
            chunk_index=0,
            content=f"Document {index} mentions renewal in December 2025.",
            page_number=index,
            embedding=[float(index)] + [0.0] * 383,
        )
        db_session.add(document)
        db_session.add(chunk)
        documents.append(document)
    await db_session.commit()
    return documents


@pytest.mark.asyncio
async def test_create_multi_document_chat_session(db_session, two_ready_documents):
    session = await chat_service.create_multi_chat_session(
        db_session,
        MultiChatSessionCreateRequest(document_ids=[doc.id for doc in two_ready_documents]),
    )
    assert len(session.document_ids) == 2
    assert session.document_id == two_ready_documents[0].id


@patch("app.services.chat_service.generate_followup_suggestions", return_value=["Follow up?"])
@patch("app.ai.langchain_rag.generate_answer", new_callable=AsyncMock)
@patch("app.services.rag_service.retrieve_chunks")
@pytest.mark.asyncio
async def test_multi_document_question_uses_all_document_ids(
    mock_retrieve,
    mock_generate,
    _mock_followups,
    db_session,
    two_ready_documents,
):
    chunk = DocumentChunk(
        id=uuid.uuid4(),
        document_id=two_ready_documents[0].id,
        chunk_index=0,
        content="Renewal date December 2025.",
        page_number=1,
        embedding=[1.0] + [0.0] * 383,
    )
    mock_retrieve.return_value = [RetrievedChunk(chunk=chunk, score=0.92)]
    mock_generate.return_value = "Renewal is December 2025."

    session = await chat_service.create_multi_chat_session(
        db_session,
        MultiChatSessionCreateRequest(document_ids=[doc.id for doc in two_ready_documents]),
    )
    response = await chat_service.ask_question(
        db_session,
        session.id,
        ChatMessageRequest(question="When is renewal?"),
    )

    called_ids = mock_retrieve.call_args.args[1]
    assert len(called_ids) == 2
    assert response.suggested_followups == ["Follow up?"]


@patch("app.ai.langchain_rag.stream_answer")
@patch("app.services.rag_service.retrieve_chunks")
@pytest.mark.asyncio
async def test_stream_question_answer_yields_tokens(
    mock_retrieve,
    mock_stream,
    db_session,
    two_ready_documents,
):
    chunk = DocumentChunk(
        id=uuid.uuid4(),
        document_id=two_ready_documents[0].id,
        chunk_index=0,
        content="Renewal date December 2025.",
        page_number=1,
        embedding=[1.0] + [0.0] * 383,
    )
    mock_retrieve.return_value = [RetrievedChunk(chunk=chunk, score=0.9)]
    async def fake_stream(*args, **kwargs):
        for token in ["Renewal ", "is December 2025."]:
            yield token

    mock_stream.side_effect = fake_stream

    session = await chat_service.create_multi_chat_session(
        db_session,
        MultiChatSessionCreateRequest(document_ids=[two_ready_documents[0].id]),
    )
    tokens = []
    async for token in chat_service.stream_question_answer(
        db_session,
        session.id,
        ChatMessageRequest(question="When is renewal?"),
    ):
        tokens.append(token)

    assert tokens == ["Renewal ", "is December 2025."]


def test_create_multi_chat_session_api(client):
    from app.db.sync_session import SessionLocal

    doc_ids = []
    session = SessionLocal()
    try:
        for name in ("a.pdf", "b.pdf"):
            doc_id = uuid.uuid4()
            doc_ids.append(doc_id)
            session.add(
                Document(
                    id=doc_id,
                    filename=name,
                    content_type="application/pdf",
                    file_path=f"/tmp/{name}",
                    file_size_bytes=100,
                    status=DocumentStatus.READY,
                    chunk_count=0,
                )
            )
        session.commit()
    finally:
        session.close()

    response = client.post(
        "/api/v1/chat/sessions",
        json={"document_ids": [str(doc_id) for doc_id in doc_ids]},
    )
    assert response.status_code == 201
    payload = response.json()
    assert len(payload["document_ids"]) == 2

    cleanup = SessionLocal()
    try:
        created_session_id = uuid.UUID(payload["id"])
        cleanup.query(ChatSessionDocument).filter(
            ChatSessionDocument.session_id == created_session_id
        ).delete()
        cleanup.query(Document).filter(Document.id.in_(doc_ids)).delete()
        cleanup.commit()
    finally:
        cleanup.close()


def test_stream_chat_message_endpoint(client):
    from app.db.sync_session import SessionLocal
    from app.models import ChatSession

    doc_id = uuid.uuid4()
    session_id = uuid.uuid4()
    db = SessionLocal()
    try:
        db.add(
            Document(
                id=doc_id,
                filename="stream.pdf",
                content_type="application/pdf",
                file_path="/tmp/stream.pdf",
                file_size_bytes=100,
                status=DocumentStatus.READY,
                chunk_count=0,
            )
        )
        db.add(ChatSession(id=session_id, document_id=doc_id, title="Stream test"))
        db.add(ChatSessionDocument(session_id=session_id, document_id=doc_id))
        db.commit()
    finally:
        db.close()

    async def fake_stream(db, session_id, payload):
        for token in ["Hello", " world"]:
            yield token

    with patch("app.api.v1.chat.chat_service.stream_question_answer", side_effect=fake_stream):
        response = client.post(
            f"/api/v1/chat/sessions/{session_id}/messages/stream",
            json={"question": "Hi"},
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = [line for line in response.text.splitlines() if line.startswith("data: ")]
    payloads = [json.loads(line.removeprefix("data: ")) for line in events]
    assert payloads[0]["token"] == "Hello"
    assert payloads[-1]["done"] is True

    cleanup = SessionLocal()
    try:
        cleanup.query(ChatSessionDocument).filter(
            ChatSessionDocument.session_id == session_id
        ).delete()
        cleanup.query(ChatSession).filter(ChatSession.id == session_id).delete()
        cleanup.query(Document).filter(Document.id == doc_id).delete()
        cleanup.commit()
    finally:
        cleanup.close()
