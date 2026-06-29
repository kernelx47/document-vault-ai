#!/usr/bin/env python3
"""Process all demo-docs through the ingestion pipeline into pgvector.

Usage (from repo root, with Docker running):
    cd backend && source .venv/bin/activate
    python ../scripts/process_demo_docs_local.py

Requires Postgres and Redis to be reachable at the URLs in .env.
Does NOT require the API or Celery worker — calls ingestion directly.
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))


def main() -> int:
    from app.db.sync_session import SessionLocal
    from app.models import Document, DocumentStatus
    from app.services.ingestion_service import process_document

    session = SessionLocal()
    try:
        docs = (
            session.query(Document)
            .filter(Document.status != DocumentStatus.READY)
            .order_by(Document.created_at.asc())
            .all()
        )
        total = session.query(Document).count()
        ready_before = session.query(Document).filter(Document.status == DocumentStatus.READY).count()
    finally:
        session.close()

    print(f"Total docs in DB: {total}")
    print(f"Already ready: {ready_before}")
    print(f"To process: {len(docs)}")

    if not docs:
        print("Nothing to do.")
        return 0

    succeeded = 0
    failed_list: list[str] = []

    for index, doc in enumerate(docs, start=1):
        print(f"[{index}/{len(docs)}] {doc.filename} (was {doc.status.value}) ... ", end="", flush=True)
        try:
            process_document(doc.id)
            print("ready")
            succeeded += 1
        except Exception as exc:
            short = str(exc)[:120]
            print(f"FAILED: {short}")
            failed_list.append(doc.filename)

    session = SessionLocal()
    try:
        ready_after = session.query(Document).filter(Document.status == DocumentStatus.READY).count()
        total_chunks = session.query(Document.chunk_count).all()
        chunks = sum(c for (c,) in total_chunks)
    finally:
        session.close()

    print(f"\n{'='*60}")
    print(f"Processed: {succeeded} succeeded, {len(failed_list)} failed")
    print(f"Ready now: {ready_after}/{total}  |  Total chunks: {chunks}")
    if failed_list:
        print(f"Failed: {failed_list[:20]}")
    return 0 if not failed_list else 1


if __name__ == "__main__":
    raise SystemExit(main())
