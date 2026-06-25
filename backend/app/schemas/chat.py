from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import MessageRole
from app.schemas.openapi_examples import CHAT_MESSAGE_EXAMPLE, CHAT_MESSAGE_REQUEST_EXAMPLE


class Citation(BaseModel):
    chunk_id: UUID
    page_number: int | None = None
    excerpt: str
    score: float


class ChatSessionCreateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    document_ids: list[UUID] = Field(default_factory=list)
    title: str | None = None
    created_at: datetime


class ChatSessionDetail(ChatSessionCreateResponse):
    model_config = ConfigDict(from_attributes=True)

    updated_at: datetime
    message_count: int = 0


class MultiChatSessionCreateRequest(BaseModel):
    document_ids: list[UUID] = Field(min_length=1, max_length=10)
    title: str | None = Field(default=None, max_length=512)


class ChatMessageRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [CHAT_MESSAGE_REQUEST_EXAMPLE]})

    question: str = Field(min_length=1, max_length=4000)


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={"examples": [CHAT_MESSAGE_EXAMPLE]},
    )

    id: UUID
    role: MessageRole
    content: str
    citations: list[Citation] = Field(default_factory=list)
    suggested_followups: list[str] = Field(default_factory=list)
    created_at: datetime


class ChatHistoryResponse(BaseModel):
    session_id: UUID
    document_id: UUID
    document_ids: list[UUID] = Field(default_factory=list)
    messages: list[ChatMessageResponse]
