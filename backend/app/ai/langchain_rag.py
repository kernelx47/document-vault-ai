"""RAG pipeline using LangChain for context-grounded answer generation and streaming."""

import asyncio
import logging
from collections.abc import AsyncIterator

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from app.ai.langchain_memory import chat_messages_to_langchain, get_buffered_chat_history
from app.ai.llm import generate_chat_answer, get_chat_llm, stream_chat_answer
from app.ai.prompts import (
    build_chat_prompt,
    get_chat_system_prompt,
    get_contextualize_prompt,
    get_grounding_suffix,
)
from app.ai.retrieval import RetrievedChunk, build_context_blocks, build_history_blocks
from app.models import ChatMessage

log = logging.getLogger("app.rag")

_GROUNDING_SUFFIX = """

## Document Context (use ONLY this to answer — cite with [Source N]):
{context}
""" + get_grounding_suffix()


def _build_prompt_chain(llm):
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", get_chat_system_prompt() + _GROUNDING_SUFFIX),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )
    return prompt | llm


async def contextualize_question(
    question: str,
    history_messages: list[ChatMessage],
) -> str:
    """Rewrite a follow-up question into a standalone search query."""
    if not history_messages:
        return question

    llm = get_chat_llm()
    if llm is None:
        return question

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", get_contextualize_prompt()),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )
    chain = prompt | llm
    try:
        response = await chain.ainvoke(
            {
                "input": question,
                "chat_history": chat_messages_to_langchain(history_messages),
            }
        )
    except Exception as exc:
        log.warning("Query contextualization failed — using original question: %s", exc)
        return question

    content = response.content if hasattr(response, "content") else str(response)
    rewritten = content.strip() if isinstance(content, str) else str(content).strip()
    if rewritten and rewritten != question:
        log.debug("Contextualized query: %r -> %r", question, rewritten)
    return rewritten or question


async def _answer_with_memory_chain(
    question: str,
    context_blocks: list[str],
    history_messages: list[ChatMessage],
) -> str:
    llm = get_chat_llm()
    if llm is None:
        system_prompt, user_prompt = build_chat_prompt(
            question,
            context_blocks,
            build_history_blocks(history_messages),
        )
        return generate_chat_answer(system_prompt, user_prompt)

    chain = _build_prompt_chain(llm)
    response = await chain.ainvoke(
        {
            "context": "\n\n".join(context_blocks) if context_blocks else "No relevant context found.",
            "chat_history": get_buffered_chat_history(history_messages),
            "input": question,
        }
    )
    content = response.content if hasattr(response, "content") else str(response)
    return content if isinstance(content, str) else str(content)


async def _stream_with_memory_chain(
    question: str,
    context_blocks: list[str],
    history_messages: list[ChatMessage],
) -> AsyncIterator[str]:
    llm = get_chat_llm()
    if llm is None:
        system_prompt, user_prompt = build_chat_prompt(
            question,
            context_blocks,
            build_history_blocks(history_messages),
        )
        for token in stream_chat_answer(system_prompt, user_prompt):
            yield token
        return

    chain = _build_prompt_chain(llm)
    async for chunk in chain.astream(
        {
            "context": "\n\n".join(context_blocks) if context_blocks else "No relevant context found.",
            "chat_history": get_buffered_chat_history(history_messages),
            "input": question,
        }
    ):
        content = chunk.content if hasattr(chunk, "content") else str(chunk)
        if content:
            yield content if isinstance(content, str) else str(content)


async def generate_answer(
    question: str,
    history_messages: list[ChatMessage],
    retrieved: list[RetrievedChunk],
) -> str:
    """Generate a complete answer grounded in retrieved document chunks with retries."""
    context_blocks = build_context_blocks(retrieved)

    last_error: Exception | None = None
    for attempt in range(3):
        try:
            answer = await _answer_with_memory_chain(question, context_blocks, history_messages)
            if answer:
                return answer
            break
        except Exception as e:
            last_error = e
            log.warning("Answer generation attempt %d/3 failed: %s", attempt + 1, e)
            if attempt < 2:
                await asyncio.sleep(1.5 * (attempt + 1))

    log.error("All answer generation attempts exhausted: %s", last_error)
    return "I'm sorry, I encountered an error generating the response. Please try again."


async def stream_answer(
    question: str,
    history_messages: list[ChatMessage],
    retrieved: list[RetrievedChunk],
) -> AsyncIterator[str]:
    """Stream a token-by-token answer grounded in retrieved document chunks with retries."""
    context_blocks = build_context_blocks(retrieved)

    last_error: Exception | None = None
    for attempt in range(3):
        try:
            async for token in _stream_with_memory_chain(question, context_blocks, history_messages):
                yield token
            return
        except Exception as e:
            last_error = e
            log.warning("Stream attempt %d/3 failed: %s", attempt + 1, e)
            if attempt < 2:
                await asyncio.sleep(1.5 * (attempt + 1))

    log.error("All stream attempts exhausted: %s", last_error)
    yield "I'm sorry, I encountered an error generating the response. Please try again."
