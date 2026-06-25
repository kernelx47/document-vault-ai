import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.chat import ChatSession
    from app.models.document import Document


class ChatSessionDocument(Base):
    __tablename__ = "chat_session_documents"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), primary_key=True
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True, index=True
    )

    session: Mapped["ChatSession"] = relationship(back_populates="session_documents")
    document: Mapped["Document"] = relationship()
