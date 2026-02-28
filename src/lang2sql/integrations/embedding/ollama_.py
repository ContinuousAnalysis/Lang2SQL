from __future__ import annotations

from ...core.exceptions import IntegrationMissingError
from ...core.ports import EmbeddingPort

try:
    import ollama as _ollama  # type: ignore[import]
except ImportError:
    _ollama = None  # type: ignore[assignment]


class OllamaEmbedding(EmbeddingPort):
    """EmbeddingPort implementation backed by the Ollama Embeddings API."""

    def __init__(
        self,
        *,
        model: str,
        base_url: str = "http://localhost:11434",
    ) -> None:
        if _ollama is None:
            raise IntegrationMissingError(
                "ollama", hint="pip install ollama"
            )
        self._model = model
        self._client = _ollama.Client(host=base_url)

    def embed_query(self, text: str) -> list[float]:
        resp = self._client.embed(model=self._model, input=text)
        return resp.embeddings[0]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        resp = self._client.embed(model=self._model, input=texts)
        return resp.embeddings
