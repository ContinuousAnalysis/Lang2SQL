from __future__ import annotations

from ...core.exceptions import IntegrationMissingError
from ...core.ports import EmbeddingPort

try:
    from sentence_transformers import SentenceTransformer as _SentenceTransformer  # type: ignore[import]
except ImportError:
    _SentenceTransformer = None  # type: ignore[assignment]


class HuggingFaceEmbedding(EmbeddingPort):
    """EmbeddingPort implementation backed by sentence-transformers."""

    def __init__(self, *, model: str) -> None:
        if _SentenceTransformer is None:
            raise IntegrationMissingError(
                "sentence-transformers",
                hint="pip install sentence-transformers",
            )
        self._model = _SentenceTransformer(model)

    def embed_query(self, text: str) -> list[float]:
        return self._model.encode(text, convert_to_numpy=True).tolist()

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return self._model.encode(texts, convert_to_numpy=True).tolist()
