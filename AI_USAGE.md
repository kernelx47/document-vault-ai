# AI Usage

## Tools

Built with Cursor IDE (Claude) as the primary coding assistant. The workflow was iterative: I'd outline what I needed architecturally, review what was generated, and refine or rewrite as needed.

## What I Designed

The architecture and key technical decisions were mine. I chose pgvector over a standalone vector DB to keep the stack simple, one Postgres instance for relational data and embeddings, one `docker compose up` to run everything. I also designed the provider abstraction layer so I could swap between local MiniLM embeddings, OpenAI, and Gemini without touching service code, using protocol-based interfaces in `ai/embeddings.py` and `ai/llm.py`.

The RAG pipeline parameters took real iteration. I tested chunk sizes from 400 to 1200 characters and settled on 800 with 150-char overlap as the sweet spot, smaller chunks lost too much context for multi-paragraph answers, larger ones diluted relevance scores and wasted tokens. top-k=5 was chosen after testing with documents of varying density; 3 wasn't enough for broad questions and 10 added noise without improving answer quality. I also chose to re-retrieve on every turn rather than reuse cached chunks from earlier in the conversation, because follow-up questions often shift topic enough that old context becomes misleading.

The guardrails were a two-tier design: fast regex patterns for obvious prompt injection and abuse, then OpenAI's Moderation API (`omni-moderation-latest`) as a second pass for nuanced content classification. On the output side, I added PII redaction (SSNs, card numbers, emails, phone numbers) and system information leak detection to prevent the LLM from exposing internal details like database schemas or file paths. The Celery pipeline uses per-stage job tracking (extract, chunk, embed, store, summarize) so failures are traceable to the exact step, and conversation memory is windowed to the last 4 turns to stay within token budgets on longer sessions.

## Where AI Helped

AI was most useful on the boilerplate-heavy parts: SQLAlchemy models, Pydantic schemas, FastAPI route scaffolding, Docker Compose config. Things that are tedious to write from scratch but straightforward to review and adjust. I also used it to draft initial prompt templates for the RAG system and to scaffold the Next.js frontend components, though both needed significant manual refinement.

## Where I Intervened

The LLM doesn't reliably follow citation format instructions. It hallucinates `[Source N]` markers that reference chunks outside the retrieved context, sometimes inventing source numbers entirely. I wrote `strip_invalid_citations` with regex-based validation that checks every `[Source N]` against the actual retrieved count, strips the invalid ones, and cleans up the leftover whitespace and punctuation so the response still reads naturally. Without this, users would see confident-looking citations pointing to nothing.

Celery doesn't support async, but the AI-generated worker code used the same async SQLAlchemy sessions from the API layer. That compiled fine but failed at runtime inside the sync Celery task executor. I had to build a separate sync session factory in `db/sync_session.py` that swaps the `asyncpg` driver for `psycopg2` at the connection URL level, with its own engine and session lifecycle. This also meant the ingestion pipeline needed to be rewritten as fully synchronous, including the embedding calls.

The output guardrails had a subtler problem. The system leak detection regex blocks technology names like "postgresql", "fastapi", and "sqlalchemy" in LLM responses to prevent exposing internal architecture. But if a user uploads a technical document that discusses those exact technologies, the guardrails would redact legitimate answers about the user's own documents. I had to scope the patterns more carefully, checking for leak indicators like connection strings and file paths rather than just keyword presence.

Embedding provider switching broke vector search silently. Swapping from `all-MiniLM-L6-v2` (384-dim) to OpenAI's `text-embedding-3-small` (1536-dim) didn't error, but cosine similarity against a 384-dim pgvector column returned garbage scores. I added dimension validation at startup that compares the provider's output dimension against the `EMBEDDING_DIMENSION` config and the actual pgvector column definition, failing fast with a clear error instead of returning bad search results.

## Process

My workflow was to design the component myself, describe it to the AI at an architectural level, review the generated implementation, then test it against real documents and fix what broke. For the RAG pipeline specifically, the actual engineering time went into tuning retrieval parameters and prompt templates, not writing code. I'd upload a batch of test documents, run the same questions with different chunk sizes and overlap values, compare the retrieved context quality, and adjust. The code was the easy part; getting the retrieval to surface the right passages consistently was where most of the effort went.

AI was a real time saver on the mechanical work: CRUD endpoints, schema definitions, model boilerplate, Docker config. But it didn't replace needing to understand how pgvector HNSW indexes behave under different dimensionalities, how LangChain chains compose and where they swallow errors, or how to debug a Celery task that hangs because it's waiting on an async event loop that doesn't exist in a sync worker.
