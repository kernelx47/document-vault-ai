#!/usr/bin/env bash
# Bulk upload all demo-docs PDFs and wait until embeddings are in pgvector.
set -euo pipefail

API_BASE_URL="${API_BASE_URL:-http://localhost:8000/api/v1}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCS_DIR="${DOCS_DIR:-$REPO_ROOT/demo-docs}"
BATCH_SIZE="${BATCH_SIZE:-25}"
POLL_INTERVAL="${POLL_INTERVAL:-5}"
MAX_WAIT_MINUTES="${MAX_WAIT_MINUTES:-180}"

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required." >&2
  exit 1
fi

mapfile -t PDF_FILES < <(find "$DOCS_DIR" -maxdepth 1 -name '*.pdf' | sort)
TOTAL="${#PDF_FILES[@]}"

if [[ "$TOTAL" -eq 0 ]]; then
  echo "No PDFs found in $DOCS_DIR" >&2
  exit 1
fi

echo "== Health check =="
curl -sS "$API_BASE_URL/health" | jq .

echo "== Uploading $TOTAL PDFs in batches of $BATCH_SIZE =="
UPLOADED=0
FAILED=0
BATCH_NUM=0

for ((offset = 0; offset < TOTAL; offset += BATCH_SIZE)); do
  BATCH_NUM=$((BATCH_NUM + 1))
  END=$((offset + BATCH_SIZE))
  if [[ "$END" -gt "$TOTAL" ]]; then
    END=$TOTAL
  fi
  COUNT=$((END - offset))
  echo "Batch $BATCH_NUM: files $((offset + 1))-$END of $TOTAL"

  CURL_ARGS=()
  for ((i = offset; i < END; i++)); do
    CURL_ARGS+=(-F "files=@${PDF_FILES[$i]}")
  done

  RESPONSE=$(curl -sS -X POST "$API_BASE_URL/documents/upload/batch" "${CURL_ARGS[@]}")
  if echo "$RESPONSE" | jq -e '.queued_count' >/dev/null 2>&1; then
    QUEUED=$(echo "$RESPONSE" | jq -r '.queued_count')
    BATCH_FAILED=$(echo "$RESPONSE" | jq -r '.failed_count')
    UPLOADED=$((UPLOADED + QUEUED))
    FAILED=$((FAILED + BATCH_FAILED))
    echo "  queued=$QUEUED failed=$BATCH_FAILED"
    if [[ "$BATCH_FAILED" -gt 0 ]]; then
      echo "$RESPONSE" | jq '.failed'
    fi
  else
    echo "Batch upload failed:" >&2
    echo "$RESPONSE" | jq . >&2 || echo "$RESPONSE" >&2
    exit 1
  fi

  sleep 2
done

echo "Upload complete: $UPLOADED queued, $FAILED failed"

echo "== Waiting for processing (max ${MAX_WAIT_MINUTES}m) =="
DEADLINE=$((SECONDS + MAX_WAIT_MINUTES * 60))
while [[ "$SECONDS" -lt "$DEADLINE" ]]; do
  METRICS=$(curl -sS "$API_BASE_URL/metrics/documents")
  READY=$(echo "$METRICS" | jq -r '.ready')
  PENDING=$(echo "$METRICS" | jq -r '.pending')
  PROCESSING=$(echo "$METRICS" | jq -r '.processing')
  FAILED_DB=$(echo "$METRICS" | jq -r '.failed')
  CHUNKS=$(echo "$METRICS" | jq -r '.total_chunks')
  TOTAL_DB=$(echo "$METRICS" | jq -r '.total')

  echo "[$(date +%H:%M:%S)] total=$TOTAL_DB ready=$READY processing=$PROCESSING pending=$PENDING failed=$FAILED_DB chunks=$CHUNKS"

  if [[ "$READY" -ge "$UPLOADED" && "$PENDING" -eq 0 && "$PROCESSING" -eq 0 ]]; then
    echo "== All documents processed =="
    echo "$METRICS" | jq .
    exit 0
  fi

  sleep "$POLL_INTERVAL"
done

echo "Timed out after ${MAX_WAIT_MINUTES} minutes." >&2
curl -sS "$API_BASE_URL/metrics/documents" | jq .
exit 1
