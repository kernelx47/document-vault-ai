import uuid

from app.services.ingestion_service import process_document
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.tasks.ping")
def ping() -> str:
    return "pong"


@celery_app.task(name="app.workers.tasks.process_document", bind=True, max_retries=0)
def process_document_task(self, document_id: str) -> str:
    process_document(uuid.UUID(document_id))
    return document_id
