from __future__ import annotations

from ...core.exceptions import IntegrationMissingError
from ...core.ports import EmbeddingPort

try:
    import openai as _openai
except ImportError:
    _openai = None  # type: ignore[assignment]


class AzureOpenAIEmbedding(EmbeddingPort):
    """EmbeddingPort implementation backed by the Azure OpenAI Embeddings API."""

    def __init__(
        self,
        *,
        azure_deployment: str,
        azure_endpoint: str,
        api_version: str = "2023-07-01-preview",
        api_key: str | None = None,
    ) -> None:
        if _openai is None:
            raise IntegrationMissingError(
                "openai", hint="pip install openai  # or: uv sync"
            )
        self._client = _openai.AzureOpenAI(
            api_key=api_key,
            azure_endpoint=azure_endpoint,
            api_version=api_version,
        )
        self._deployment = azure_deployment

    def embed_query(self, text: str) -> list[float]:
        return (
            self._client.embeddings.create(input=text, model=self._deployment)
            .data[0]
            .embedding
        )

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        resp = self._client.embeddings.create(input=texts, model=self._deployment)
        return [item.embedding for item in resp.data]
