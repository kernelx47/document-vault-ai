from collections.abc import AsyncIterator
from uuid import UUID

from langchain_classic.chains import create_history_aware_retriever, create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.retrievers import BaseRetriever
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.langchain_memory import chat_messages_to_langchain, get_buffered_chat_history
from app.ai.llm import generate_chat_answer, get_chat_llm, stream_chat_answer
from app.ai.prompts import CHAT_SYSTEM_PROMPT, build_chat_prompt
from app.models import ChatMessage
from app.ai.retrieval import RetrievedChunk, build_context_blocks, build_history_blocks, retrieve_chunks

CONTEXTUALIZE_Q_SYSTEM_PROMPT = """Given the chat history and the latest user question about uploaded document(s),
rewrite the question into a standalone search query.
Do not answer the question. Return the original question if no rewrite is needed."""


class PgVectorChunkRetriever(BaseRetriever):
    db: AsyncSession
    document_ids: list[UUID]

    class Config:
        arbitrary_types_allowed = True

    async def _aget_relevant_documents(self, query: str) -> list[Document]:
        retrieved = await retrieve_chunks(self.db, self.document_ids, query)
        documents: list[Document] = []
        for block, item in zip(build_context_blocks(retrieved), retrieved, strict=True):
            documents.append(
                Document(
                    page_content=block,
                    metadata={
                        "chunk_id": str(item.chunk.id),
                        "page_number": item.chunk.page_number,
                        "score": item.score,
                    },
                )
            )
        return documents

    def _get_relevant_documents(self, query: str) -> list[Document]:
        raise NotImplementedError("Use async retrieval via the LangChain RAG chain.")


def _build_prompt_chain(llm):
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", CHAT_SYSTEM_PROMPT + "\n\nContext:\n{context}"),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )
    return prompt | llm


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


def build_history_aware_rag_chain(db: AsyncSession, document_ids: list[UUID]):
    llm = get_chat_llm()
    if llm is None:
        return None

    retriever = PgVectorChunkRetriever(db=db, document_ids=document_ids)
    contextualize_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", CONTEXTUALIZE_Q_SYSTEM_PROMPT),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )
    history_aware_retriever = create_history_aware_retriever(
        llm,
        retriever,
        contextualize_prompt,
    )
    qa_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", CHAT_SYSTEM_PROMPT),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )
    question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)
    return create_retrieval_chain(history_aware_retriever, question_answer_chain)


async def generate_answer(
    db: AsyncSession,
    document_ids: list[UUID],
    question: str,
    history_messages: list[ChatMessage],
    retrieved: list[RetrievedChunk],
) -> str:
    context_blocks = build_context_blocks(retrieved)
    chain = build_history_aware_rag_chain(db, document_ids)
    if chain is not None:
        result = await chain.ainvoke(
            {
                "input": question,
                "chat_history": chat_messages_to_langchain(history_messages),
            }
        )
        answer = result.get("answer", "")
        if answer:
            return str(answer)

    return await _answer_with_memory_chain(question, context_blocks, history_messages)


async def stream_answer(
    db: AsyncSession,
    document_ids: list[UUID],
    question: str,
    history_messages: list[ChatMessage],
    retrieved: list[RetrievedChunk],
) -> AsyncIterator[str]:
    context_blocks = build_context_blocks(retrieved)
    async for token in _stream_with_memory_chain(question, context_blocks, history_messages):
        yield token
