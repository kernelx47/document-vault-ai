# Document Vault AI

Upload PDF and DOCX files, ask questions, get answers grounded in your documents with source citations.

## Architecture

```
Next.js UI ──▶ FastAPI ──▶ PostgreSQL + pgvector
                 │              ▲
                 ▼              │
               Redis ──▶ Celery Worker ──▶ Embeddings + LLM
```

**Backend:** FastAPI, SQLAlchemy (async), Celery, Redis, LangChain, pgvector
**Frontend:** Next.js 14, TypeScript, Tailwind CSS, Recharts
**Infrastructure:** Docker Compose (5 services), Alembic migrations

## Getting Started

```bash
cp .env.example .env       # add your OpenAI or Gemini API key
docker compose up --build
```

| Service   | URL                          |
|-----------|------------------------------|
| Frontend  | http://localhost:3000         |
| API       | http://localhost:8000         |
| Swagger   | http://localhost:8000/docs    |

## How It Works

### Document Ingestion

Upload triggers an async Celery task that runs a five-stage pipeline: extract text (pdfplumber for PDFs, python-docx for DOCX), split into 800-character chunks with 150-char overlap, generate 384-dimensional embeddings using `all-MiniLM-L6-v2`, store the vectors in a pgvector HNSW-indexed column, and produce an AI-generated summary with key insights and document classification (category, tags, sentiment). Each stage is tracked independently in `processing_jobs` so failures are traceable to the exact step.

### Embedding and Vector Search

Documents are embedded locally using sentence-transformers (`all-MiniLM-L6-v2`), producing 384-dimensional vectors stored in PostgreSQL via pgvector. At query time, the user's question is embedded with the same model and matched against stored chunks using cosine similarity. The system retrieves the top-5 most relevant chunks, filters out anything below a 0.2 similarity threshold, and passes the context to the LLM. Embedding is batched (32 chunks per call) during ingestion to keep processing time reasonable on larger documents.

### RAG Chat

Follow-up questions are rewritten into standalone search queries using LangChain so retrieval isn't biased by conversational context. The retrieved chunks are formatted as `[Source N]` blocks and injected into the system prompt with grounding instructions. The LLM generates an answer citing specific sources, and a post-generation step validates every `[Source N]` reference against the actual retrieved context, stripping any hallucinated citations. Conversation history is windowed to the last 4 turns to stay within token limits. Responses can be streamed via SSE.

### Guardrails

Input guardrails are two-tiered: a fast regex layer catches prompt injection attempts (instruction overrides, role hijacking, system prompt extraction, SQL/code injection, XSS, template injection, jailbreak patterns), then OpenAI's Moderation API (`omni-moderation-latest`) handles nuanced content classification across 13 harm categories. Output guardrails redact PII (SSNs, credit card numbers, emails, phone numbers, tax IDs) and detect system information leaks (internal paths, connection strings, technology stack references) before the response reaches the user.

## API

Base path: `/api/v1`

| Endpoint | Description |
|----------|-------------|
| `POST /documents/upload` | Upload PDF/DOCX (single or batch) |
| `GET /documents` | List documents with status |
| `GET /documents/{id}/insights` | AI-generated summary and key insights |
| `POST /documents/compare` | Multi-document comparison |
| `POST /documents/{id}/chat/sessions` | Start a chat session |
| `POST /chat/sessions/{id}/messages` | Ask a question (supports SSE streaming) |
| `GET /metrics/*` | Processing stats, RAG performance, AI usage |
| `GET /health` | DB, Redis, and worker health |

## Configuration

AI providers are swappable via environment variables:

| Variable | Options | Default |
|----------|---------|---------|
| `EMBEDDING_PROVIDER` | `local`, `openai`, `gemini` | `local` |
| `LLM_PROVIDER` | `openai`, `gemini`, `ollama` | `openai` |
| `RAG_TOP_K` | 1-20 | `5` |
| `CHUNK_SIZE` | chars | `800` |
| `CHUNK_OVERLAP` | chars | `150` |

Local embeddings (`all-MiniLM-L6-v2`, 384-dim) require no API key. See `.env.example` for the full list.

## Limitations

- English language only
- 20 MB file size limit
- Scanned/image-based PDFs not supported (no OCR)
- File storage is local disk (not S3)
