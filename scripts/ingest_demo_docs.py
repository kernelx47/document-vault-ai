#!/usr/bin/env python3
"""Upload demo-docs PDFs via API and wait until all are embedded in pgvector."""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = REPO_ROOT / "demo-docs"
API_BASE = "http://localhost:8000/api/v1"
BATCH_SIZE = 25
POLL_SECONDS = 5
MAX_WAIT_MINUTES = 180


def api_get(path: str) -> dict:
    with urllib.request.urlopen(f"{API_BASE}{path}") as response:
        return json.load(response)


def api_post_multipart(path: str, files: list[Path]) -> dict:
    boundary = "----DocumentVaultBulkUpload"
    body_parts: list[bytes] = []
    for file_path in files:
        content = file_path.read_bytes()
        body_parts.append(
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="files"; filename="{file_path.name}"\r\n'
            f"Content-Type: application/pdf\r\n\r\n".encode()
            + content
            + b"\r\n"
        )
    body_parts.append(f"--{boundary}--\r\n".encode())
    body = b"".join(body_parts)
    request = urllib.request.Request(
        f"{API_BASE}{path}",
        data=body,
        method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)


def existing_documents() -> dict[str, str]:
    """Map filename -> status."""
    by_name: dict[str, str] = {}
    page = 1
    while True:
        data = api_get(f"/documents?page={page}&page_size=100")
        for item in data["items"]:
            by_name[item["filename"]] = item["status"]
        if page * 100 >= data["total"]:
            break
        page += 1
    return by_name


def main() -> int:
    demo_pdfs = sorted(DOCS_DIR.glob("*.pdf"))
    if not demo_pdfs:
        print(f"No PDFs in {DOCS_DIR}", file=sys.stderr)
        return 1

    print("== Health ==")
    health = api_get("/health")
    print(json.dumps(health, indent=2))
    if health.get("status") != "ok":
        print("API not healthy — start docker compose first.", file=sys.stderr)
        return 1

    known = existing_documents()
    to_upload = [pdf for pdf in demo_pdfs if pdf.name not in known]
    already = [pdf for pdf in demo_pdfs if pdf.name in known]

    print(f"Demo PDFs: {len(demo_pdfs)}")
    print(f"Already in DB: {len(already)}")
    print(f"To upload: {len(to_upload)}")

    uploaded = 0
    for start in range(0, len(to_upload), BATCH_SIZE):
        batch = to_upload[start : start + BATCH_SIZE]
        print(f"Uploading batch {start // BATCH_SIZE + 1}: {len(batch)} files...")
        try:
            result = api_post_multipart("/documents/upload/batch", batch)
        except urllib.error.HTTPError as exc:
            print(exc.read().decode(), file=sys.stderr)
            return 1
        uploaded += result["queued_count"]
        print(
            f"  queued={result['queued_count']} failed={result['failed_count']} — {result['message']}"
        )
        if result["failed"]:
            print(json.dumps(result["failed"], indent=2))
        time.sleep(2)

    print(f"Queued {uploaded} new documents.")

    deadline = time.time() + MAX_WAIT_MINUTES * 60
    target_names = {pdf.name for pdf in demo_pdfs}

    while time.time() < deadline:
        known = existing_documents()
        statuses = {name: known.get(name, "missing") for name in target_names}
        ready = sum(1 for s in statuses.values() if s == "ready")
        pending = sum(1 for s in statuses.values() if s in {"pending", "processing"})
        failed = sum(1 for s in statuses.values() if s == "failed")
        missing = sum(1 for s in statuses.values() if s == "missing")
        metrics = api_get("/metrics/documents")

        print(
            f"[{time.strftime('%H:%M:%S')}] demo ready={ready}/{len(target_names)} "
            f"pending={pending} failed={failed} missing={missing} "
            f"chunks={metrics['total_chunks']}"
        )

        if ready == len(target_names):
            print("\n== All demo documents embedded in pgvector ==")
            print(json.dumps(metrics, indent=2))
            return 0

        if pending == 0 and missing == 0 and failed > 0:
            failed_names = [n for n, s in statuses.items() if s == "failed"]
            print("Some documents failed:", failed_names[:10], file=sys.stderr)
            return 1

        time.sleep(POLL_SECONDS)

    print("Timed out waiting for processing.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
