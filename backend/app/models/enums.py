import enum


class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class ProcessingJobStatus(str, enum.Enum):
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
