#!/usr/bin/env python3
"""Re-queue failed demo documents for Celery processing."""

from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = REPO_ROOT / "demo-docs"
API_BASE = "http://localhost:8000/api/v1"
POLL_SECONDS = 10
MAX_WAIT_MINUTES = 240


def api_get(path: str) -> dict:
    with urllib.request.urlopen(f"{API_BASE}{path}") as response:
        return json.load(response)


def demo_documents() -> list[dict]:
    target_names = {path.name for path in DOCS_DIR.glob("*.pdf")}
    matches: list[dict] = []
    page = 1
    while True:
        data = api_get(f"/documents?page={page}&page_size=100")
        for item in data["items"]:
            if item["filename"] in target_names:
                matches.append(item)
        if page * 100 >= data["total"]:
            break
        page += 1
    return matches


def main() -> int:
    try:
        from app.workers.tasks import process_document_task
    except ImportError:
        print("Run from backend venv: cd backend && source .venv/bin/activate", file=sys.stderr)
        return 1

    docs = demo_documents()
    failed = [doc for doc in docs if doc["status"] == "failed"]
    print(f"Demo docs in DB: {len(docs)}")
    print(f"Failed to reprocess: {len(failed)}")

    for doc in failed:
        process_document_task.delay(doc["id"])
        print(f"  queued {doc['filename']}")

    target_names = {path.name for path in DOCS_DIR.glob("*.pdf")}
    deadline = time.time() + MAX_WAIT_MINUTES * 60

    while time.time() < deadline:
        docs = demo_documents()
        statuses = {doc["filename"]: doc["status"] for doc in docs}
        ready = sum(1 for name in target_names if statuses.get(name) == "ready")
        pending = sum(
            1 for name in target_names if statuses.get(name) in {"pending", "processing"}
        )
        failed_count = sum(1 for name in target_names if statuses.get(name) == "failed")
        metrics = api_get("/metrics/documents")
        print(
            f"[{time.strftime('%H:%M:%S')}] ready={ready}/{len(target_names)} "
            f"pending={pending} failed={failed_count} chunks={metrics['total_chunks']}"
        )
        if ready == len(target_names):
            print(json.dumps(metrics, indent=2))
            return 0
        if pending == 0 and failed_count > 0:
            print("Processing finished with failures.", file=sys.stderr)
            return 1
        time.sleep(POLL_SECONDS)

    print("Timed out.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
