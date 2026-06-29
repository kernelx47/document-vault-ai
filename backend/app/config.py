"""Application settings loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables and .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    secret_key: str = "change-me"

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/document_vault"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    celery_queue_name: str = "celery"

    upload_dir: str = "./uploads"
    max_upload_size_mb: int = 20
    max_batch_upload_files: int = 25
    max_multi_doc_chat_documents: int = 10
    upload_rate_limit_per_minute: int = 30
    chat_rate_limit_per_minute: int = 60
    daily_ai_request_quota: int = 1000
    embedding_batch_size: int = 32

    log_level: str = "INFO"

    openai_input_cost_per_1m_tokens: float = 0.15
    openai_output_cost_per_1m_tokens: float = 0.60
    gemini_input_cost_per_1m_tokens: float = 0.075
    gemini_output_cost_per_1m_tokens: float = 0.30

    embedding_provider: str = "local"
    llm_provider: str = "openai"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    gemini_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    chunk_size: int = 800
    chunk_overlap: int = 150
    rag_top_k: int = 5
    embedding_dimension: int = 384

    cors_origins: list[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
