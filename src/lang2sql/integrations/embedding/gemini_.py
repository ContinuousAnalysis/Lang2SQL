from __future__ import annotations

from ...core.exceptions import IntegrationMissingError
from ...core.ports import EmbeddingPort

try:
    import google.generativeai as _genai  # type: ignore[import]
except ImportError:
    _genai = None  # type: ignore[assignment]


class GeminiEmbedding(EmbeddingPort):
    """EmbeddingPort implementation backed by the Google Gemini Embeddings API."""

    def __init__(
        self,
        *,
        model: str = "models/embedding-001",
        api_key: str | None = None,
    ) -> None:
        if _genai is None:
            raise IntegrationMissingError(
                "google-generativeai",
                hint="pip install google-generativeai",
            )
        if api_key:
            _genai.configure(api_key=api_key)
        self._model = model

    def embed_query(self, text: str) -> list[float]:
        result = _genai.embed_content(
            model=self._model,
            content=text,
            task_type="retrieval_query",
        )
        return result["embedding"]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [
            _genai.embed_content(
                model=self._model,
                content=t,
                task_type="retrieval_document",
            )["embedding"]
            for t in texts
        ]
