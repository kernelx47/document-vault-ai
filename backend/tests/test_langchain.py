import uuid

import pytest

from app.ai.langchain_memory import (
    HISTORY_WINDOW,
    build_conversation_buffer,
    chat_messages_to_langchain,
    get_buffered_chat_history,
)
from app.models import ChatMessage, MessageRole


def test_chat_messages_to_langchain_limits_window():
    messages = [
        ChatMessage(
            id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            role=MessageRole.USER,
            content=f"Question {index}",
        )
        for index in range(6)
    ]

    converted = chat_messages_to_langchain(messages)

    assert len(converted) == HISTORY_WINDOW
    assert converted[0].content == "Question 2"
    assert converted[-1].content == "Question 5"


def test_conversation_buffer_window_memory():
    messages = [
        ChatMessage(
            id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            role=MessageRole.USER if index % 2 == 0 else MessageRole.ASSISTANT,
            content=f"Message {index}",
        )
        for index in range(6)
    ]

    memory = build_conversation_buffer(messages)
    buffered = get_buffered_chat_history(messages)

    assert memory.k == HISTORY_WINDOW
    assert len(buffered) <= HISTORY_WINDOW * 2
    assert buffered[-1].content == "Message 5"


@pytest.mark.asyncio
async def test_contextualize_question_returns_original_without_history():
    from app.ai.langchain_rag import contextualize_question

    result = await contextualize_question("When is renewal?", [])
    assert result == "When is renewal?"


def test_contextualize_question_returns_original_without_llm():
    from unittest.mock import patch

    from app.ai.langchain_rag import contextualize_question
    import asyncio

    messages = [
        ChatMessage(
            id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            role=MessageRole.USER,
            content="When is the renewal date?",
        ),
        ChatMessage(
            id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            role=MessageRole.ASSISTANT,
            content="December 2025.",
        ),
    ]

    with patch("app.ai.langchain_rag.get_chat_llm", return_value=None):
        result = asyncio.run(contextualize_question("What about billing?", messages))

    assert result == "What about billing?"
