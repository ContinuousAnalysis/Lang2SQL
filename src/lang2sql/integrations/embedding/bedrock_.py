from __future__ import annotations

import json

from ...core.exceptions import IntegrationMissingError
from ...core.ports import EmbeddingPort

try:
    import boto3 as _boto3  # type: ignore[import]
except ImportError:
    _boto3 = None  # type: ignore[assignment]


class BedrockEmbedding(EmbeddingPort):
    """EmbeddingPort implementation backed by AWS Bedrock Embeddings API.

    Supports Amazon Titan embedding models (e.g., amazon.titan-embed-text-v1).
    """

    def __init__(
        self,
        *,
        model_id: str,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        region_name: str = "us-east-1",
    ) -> None:
        if _boto3 is None:
            raise IntegrationMissingError("boto3", hint="pip install boto3")
        self._model_id = model_id
        self._client = _boto3.client(
            "bedrock-runtime",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name,
        )

    def _embed_single(self, text: str) -> list[float]:
        body = json.dumps({"inputText": text})
        resp = self._client.invoke_model(
            modelId=self._model_id,
            body=body,
            contentType="application/json",
            accept="application/json",
        )
        result = json.loads(resp["body"].read())
        return result["embedding"]

    def embed_query(self, text: str) -> list[float]:
        return self._embed_single(text)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_single(t) for t in texts]
