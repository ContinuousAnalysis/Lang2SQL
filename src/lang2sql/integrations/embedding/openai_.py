from __future__ import annotations

from ...core.exceptions import IntegrationMissingError

try:
    import openai as _openai
except ImportError:
    _openai = None  # type: ignore[assignment]


class OpenAIEmbedding:
    """EmbeddingPort implementation backed by OpenAI Embeddings API."""

    def __init__(self, *, model: str = "text-embedding-3-small", api_key: str | None = None) -> None:
        if _openai is None:
            raise IntegrationMissingError("openai", hint="pip install openai")
        self._client = _openai.OpenAI(api_key=api_key)
        self._model = model

    def embed_query(self, text: str) -> list[float]:
        return self._client.embeddings.create(input=text, model=self._model).data[0].embedding

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        resp = self._client.embeddings.create(input=texts, model=self._model)
        return [item.embedding for item in resp.data]
