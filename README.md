# Document Vault AI

AI-powered document management backend with RAG chat, plus a Next.js frontend shell.

## Stack

- **Backend:** FastAPI, PostgreSQL (pgvector), Celery, Redis
- **Frontend:** Next.js (App Router), TypeScript, Tailwind CSS

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

| Service  | URL |
|----------|-----|
| API      | http://localhost:8000 |
| API docs | http://localhost:8000/docs |
| Frontend | http://localhost:3000 |

## Local development

**Backend**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

AI/document dependencies install separately in Phase 1:

```bash
pip install -e ".[ai]"
```

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

Set `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1` in `.env.local`.

## Project layout

```text
backend/     FastAPI app, Celery workers, Alembic migrations
frontend/    Next.js UI
docker-compose.yml
```

## Status

Phase 0 complete — stack verified with Docker Compose, health checks, Celery worker, and frontend shell. Document ingestion starts in Phase 1.
