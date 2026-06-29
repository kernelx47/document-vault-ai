"""Shared enumerations for document, processing, and chat models."""

import enum


class DocumentStatus(str, enum.Enum):
    """Lifecycle states of a document from upload through processing."""

    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class ProcessingJobStatus(str, enum.Enum):
    """Outcome states for an individual processing pipeline stage."""

    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"


class MessageRole(str, enum.Enum):
    """Role of a chat message sender."""

    USER = "user"
    ASSISTANT = "assistant"
