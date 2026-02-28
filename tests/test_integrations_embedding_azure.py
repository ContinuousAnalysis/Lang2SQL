"""Tests for AzureOpenAIEmbedding integration."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

openai = pytest.importorskip("openai", reason="openai not installed")

from lang2sql.integrations.embedding.azure_ import AzureOpenAIEmbedding


def _make_embedding() -> AzureOpenAIEmbedding:
    return AzureOpenAIEmbedding(
        azure_deployment="text-embedding-ada-002",
        azure_endpoint="https://test.openai.azure.com/",
        api_key="test-key",
    )


def _mock_embedding_response(vectors: list[list[float]]):
    resp = MagicMock()
    resp.data = [MagicMock(embedding=v) for v in vectors]
    return resp


def test_embed_query_returns_vector():
    vec = [0.1, 0.2, 0.3]
    with patch("openai.AzureOpenAI") as MockClient:
        instance = MockClient.return_value
        instance.embeddings.create.return_value = _mock_embedding_response([vec])

        emb = _make_embedding()
        emb._client = instance
        result = emb.embed_query("hello")

    assert result == vec


def test_embed_texts_returns_multiple_vectors():
    vecs = [[0.1, 0.2], [0.3, 0.4]]
    with patch("openai.AzureOpenAI") as MockClient:
        instance = MockClient.return_value
        instance.embeddings.create.return_value = _mock_embedding_response(vecs)

        emb = _make_embedding()
        emb._client = instance
        result = emb.embed_texts(["hello", "world"])

    assert result == vecs
