"""SQLAlchemy model for uploaded documents and their metadata."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import DocumentStatus

if TYPE_CHECKING:
    from app.models.batch import UploadBatch
    from app.models.chat import ChatSession
    from app.models.chat_session_document import ChatSessionDocument
    from app.models.chunk import DocumentChunk
    from app.models.processing import ProcessingJob


class Document(Base):
    """A versioned document with processing state, AI-generated insights, and related chunks."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(
            DocumentStatus,
            values_callable=lambda enum: [item.value for item in enum],
            native_enum=False,
        ),
        default=DocumentStatus.PENDING,
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    insights: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tags: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    sentiment: Mapped[str | None] = mapped_column(String(32), nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    document_group_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_latest: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    batch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("upload_batches.id", ondelete="SET NULL"), nullable=True, index=True
    )
    processing_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processing_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    processing_jobs: Mapped[list["ProcessingJob"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    chat_sessions: Mapped[list["ChatSession"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    chat_session_links: Mapped[list["ChatSessionDocument"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    batch: Mapped["UploadBatch | None"] = relationship(back_populates="documents")
