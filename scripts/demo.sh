#!/usr/bin/env bash
# End-to-end demo: upload → process → insights → chat → metrics
set -euo pipefail

API_BASE_URL="${API_BASE_URL:-http://localhost:8000/api/v1}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FIXTURE_PATH="${FIXTURE_PATH:-$REPO_ROOT/backend/tests/fixtures/sample.pdf}"
POLL_INTERVAL="${POLL_INTERVAL:-3}"
MAX_POLLS="${MAX_POLLS:-60}"

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required. Install jq and retry." >&2
  exit 1
fi

if [[ ! -f "$FIXTURE_PATH" ]]; then
  echo "Fixture not found: $FIXTURE_PATH" >&2
  exit 1
fi

section() {
  echo
  echo "== $1 =="
}

section "1. Health check"
curl -sS "$API_BASE_URL/health" | jq .

section "2. Upload sample document"
UPLOAD_JSON=$(curl -sS -X POST "$API_BASE_URL/documents/upload" -F "file=@${FIXTURE_PATH}")
echo "$UPLOAD_JSON" | jq .
DOC_ID=$(echo "$UPLOAD_JSON" | jq -r '.id')

if [[ -z "$DOC_ID" || "$DOC_ID" == "null" ]]; then
  echo "Upload failed — no document id returned." >&2
  exit 1
fi

section "3. Poll processing status until ready"
for ((i = 1; i <= MAX_POLLS; i++)); do
  STATUS_JSON=$(curl -sS "$API_BASE_URL/documents/${DOC_ID}/status")
  STATUS=$(echo "$STATUS_JSON" | jq -r '.status')
  echo "[$i/$MAX_POLLS] status=$STATUS"
  if [[ "$STATUS" == "ready" ]]; then
    break
  fi
  if [[ "$STATUS" == "failed" ]]; then
    echo "$STATUS_JSON" | jq .
    echo "Document processing failed." >&2
    exit 1
  fi
  sleep "$POLL_INTERVAL"
done

if [[ "$STATUS" != "ready" ]]; then
  echo "Timed out waiting for document to become ready." >&2
  exit 1
fi

section "4. Fetch insights"
curl -sS "$API_BASE_URL/documents/${DOC_ID}/insights" | jq .

section "5. Start chat session"
SESSION_JSON=$(curl -sS -X POST "$API_BASE_URL/documents/${DOC_ID}/chat/sessions")
echo "$SESSION_JSON" | jq .
SESSION_ID=$(echo "$SESSION_JSON" | jq -r '.id')

section "6. Ask: What is this document about?"
curl -sS -X POST "$API_BASE_URL/chat/sessions/${SESSION_ID}/messages" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is this document about?"}' | jq .

section "7. Follow-up: When is the renewal date?"
curl -sS -X POST "$API_BASE_URL/chat/sessions/${SESSION_ID}/messages" \
  -H "Content-Type: application/json" \
  -d '{"question": "When is the renewal date?"}' | jq .

section "8. Chat history"
curl -sS "$API_BASE_URL/chat/sessions/${SESSION_ID}/messages" | jq .

section "9. Document metrics"
curl -sS "$API_BASE_URL/metrics/documents" | jq .

section "Done"
echo "Document ID: $DOC_ID"
echo "Session ID:  $SESSION_ID"
