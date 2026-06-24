from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import MessageRole


class Citation(BaseModel):
    chunk_id: UUID
    page_number: int | None = None
    excerpt: str
    score: float


class ChatSessionCreateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    title: str | None = None
    created_at: datetime


class ChatSessionDetail(ChatSessionCreateResponse):
    model_config = ConfigDict(from_attributes=True)

    updated_at: datetime
    message_count: int = 0


class ChatMessageRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: MessageRole
    content: str
    citations: list[Citation] = Field(default_factory=list)
    created_at: datetime


class ChatHistoryResponse(BaseModel):
    session_id: UUID
    document_id: UUID
    messages: list[ChatMessageResponse]
