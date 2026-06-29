from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import MessageRole
from app.schemas.openapi_examples import (
    CHAT_HISTORY_EXAMPLE,
    CHAT_MESSAGE_EXAMPLE,
    CHAT_MESSAGE_REQUEST_EXAMPLE,
    CHAT_SESSION_CREATE_EXAMPLE,
    CHAT_SESSION_DETAIL_EXAMPLE,
    MULTI_CHAT_SESSION_REQUEST_EXAMPLE,
)


class Citation(BaseModel):
    chunk_id: UUID = Field(description="ID of the source chunk in the vector store.")
    document_id: UUID | None = Field(
        default=None,
        description="ID of the source document.",
    )
    document_filename: str | None = Field(
        default=None,
        description="Filename of the source document.",
    )
    page_number: int | None = Field(default=None, description="Page number in the source document.")
    excerpt: str = Field(description="Relevant text snippet from the source chunk.")
    score: float = Field(description="Similarity score (0–1) for this citation.")
    source_index: int | None = Field(
        default=None,
        description="[Source N] index from the answer text, when the model cited this chunk.",
    )


class ChatSessionCreateResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={"examples": [CHAT_SESSION_CREATE_EXAMPLE]},
    )

    id: UUID = Field(description="Chat session ID. Pass to message endpoints.")
    document_id: UUID = Field(description="Primary document for this session.")
    document_ids: list[UUID] = Field(
        default_factory=list,
        description="All documents included in this session (single- or multi-doc).",
    )
    title: str | None = Field(default=None, description="Display title for the session.")
    created_at: datetime


class ChatSessionDetail(ChatSessionCreateResponse):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={"examples": [CHAT_SESSION_DETAIL_EXAMPLE]},
    )

    updated_at: datetime
    message_count: int = Field(default=0, description="Total messages in this session.")


class MultiChatSessionCreateRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [MULTI_CHAT_SESSION_REQUEST_EXAMPLE]})

    document_ids: list[UUID] = Field(
        min_length=1,
        max_length=10,
        description="One or more document IDs. All must be in `ready` status.",
    )
    title: str | None = Field(default=None, max_length=512, description="Optional session title.")


class ChatMessageRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [CHAT_MESSAGE_REQUEST_EXAMPLE]})

    question: str = Field(
        min_length=1,
        max_length=4000,
        description="Natural-language question about the session documents.",
    )


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={"examples": [CHAT_MESSAGE_EXAMPLE]},
    )

    id: UUID
    role: MessageRole
    content: str = Field(description="Assistant answer grounded in retrieved document chunks.")
    citations: list[Citation] = Field(
        default_factory=list,
        description="Source excerpts supporting the answer.",
    )
    suggested_followups: list[str] = Field(
        default_factory=list,
        description="Optional follow-up questions the user might ask next.",
    )
    created_at: datetime


class ChatHistoryResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [CHAT_HISTORY_EXAMPLE]})

    session_id: UUID
    document_id: UUID
    document_ids: list[UUID] = Field(default_factory=list)
    messages: list[ChatMessageResponse] = Field(description="Messages in chronological order.")
