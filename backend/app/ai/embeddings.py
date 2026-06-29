"""Embedding provider abstraction for generating vector representations of text."""

import logging
from functools import lru_cache

from app.config import get_settings

logger = logging.getLogger("app.embeddings")


class EmbeddingProvider:
    """Abstract base for text embedding providers."""

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    def embed_query(self, text: str) -> list[float]:
        vectors = self.embed_texts([text])
        return vectors[0] if vectors else []

    @property
    def dimension(self) -> int:
        return get_settings().embedding_dimension


class LocalEmbeddingProvider(EmbeddingProvider):
    """Embedding provider using a local sentence-transformers model."""
    @lru_cache(maxsize=1)
    def _model(self):
        from sentence_transformers import SentenceTransformer

        try:
            return SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        except Exception:
            logger.exception("Failed to load embedding model")
            raise

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            vectors = self._model().encode(texts, normalize_embeddings=True)
            return [vector.tolist() for vector in vectors]
        except Exception:
            logger.exception("Embedding generation failed for %d texts", len(texts))
            raise


def get_embedding_provider() -> EmbeddingProvider:
    """Instantiate the configured embedding provider."""
    settings = get_settings()
    if settings.embedding_provider == "local":
        return LocalEmbeddingProvider()
    raise RuntimeError(f"Unsupported embedding provider: {settings.embedding_provider}")
