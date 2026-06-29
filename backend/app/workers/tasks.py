"""Celery task definitions for asynchronous document processing."""

import logging
import uuid

from celery.exceptions import SoftTimeLimitExceeded

from app.services.ingestion_service import process_document
from app.workers.celery_app import celery_app

logger = logging.getLogger("app.worker")


@celery_app.task(name="app.workers.tasks.ping")
def ping() -> str:
    return "pong"


@celery_app.task(
    name="app.workers.tasks.process_document",
    bind=True,
    max_retries=2,
    autoretry_for=(ConnectionError, OSError),
    retry_backoff=True,
    retry_backoff_max=60,
)
def process_document_task(self, document_id: str) -> str:
    """Run the ingestion pipeline for a single document with automatic retries."""
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        logger.error("Invalid document_id received: %s", document_id)
        raise

    try:
        logger.info("Processing document %s (attempt %d/%d)", document_id, self.request.retries + 1, self.max_retries + 1)
        process_document(doc_uuid)
        logger.info("Document %s processed successfully", document_id)
        return document_id
    except SoftTimeLimitExceeded:
        logger.error("Document %s processing timed out", document_id)
        raise
    except Exception:
        logger.exception("Document %s processing failed", document_id)
        raise
