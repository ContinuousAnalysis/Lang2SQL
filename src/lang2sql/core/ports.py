from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from .catalog import TextDocument


class LLMPort(Protocol):
    """Abstracts LLM backends (Anthropic, OpenAI, etc.)."""

    def invoke(self, messages: list[dict[str, str]]) -> str: ...


class DBPort(Protocol):
    """Abstracts database backends (SQLAlchemy, etc.)."""

    def execute(self, sql: str) -> list[dict[str, Any]]: ...


class EmbeddingPort(Protocol):
    """Abstracts embedding backends (OpenAI, Azure, Bedrock, etc.)."""

    def embed_query(self, text: str) -> list[float]: ...

    def embed_texts(self, texts: list[str]) -> list[list[float]]: ...


class VectorStorePort(Protocol):
    """Abstracts vector store backends (InMemory, FAISS, pgvector, etc.)."""

    def search(self, vector: list[float], k: int) -> list[tuple[str, float]]:
        """
        Return the k nearest vectors.

        Returns:
            List of (chunk_id, score) sorted by score descending.
            Score range: [-1, 1] (cosine similarity).
        """
        ...

    def upsert(self, ids: list[str], vectors: list[list[float]]) -> None:
        """
        Store or update vectors by chunk_id.

        Implementations must merge incoming entries into existing ones —
        calling upsert twice must not lose entries from the first call.

        Args:
            ids:     List of chunk_ids.
            vectors: Corresponding embedding vectors (len(ids) == len(vectors)).
        """
        ...


@runtime_checkable
class DocumentLoaderPort(Protocol):
    """Converts a file path or directory to list[TextDocument]."""

    def load(self, path: str) -> list[TextDocument]: ...
