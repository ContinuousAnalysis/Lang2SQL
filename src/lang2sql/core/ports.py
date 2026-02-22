from __future__ import annotations

from typing import Protocol


class EmbeddingPort(Protocol):
    """
    Placeholder — will be implemented in OQ-2 (VectorRetriever).

    Abstracts embedding backends (OpenAI, Azure, Bedrock, etc.)
    so VectorRetriever is not coupled to any specific provider.
    """

    def embed_query(self, text: str) -> list[float]: ...

    def embed_texts(self, texts: list[str]) -> list[list[float]]: ...
