"""Tests for OllamaLLM integration."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

ollama = pytest.importorskip("ollama", reason="ollama not installed")

from lang2sql.integrations.llm.ollama_ import OllamaLLM


def test_ollama_llm_invoke_returns_string():
    mock_resp = MagicMock()
    mock_resp.message.content = "SELECT 1"

    with patch("ollama.Client") as MockClient:
        instance = MockClient.return_value
        instance.chat.return_value = mock_resp

        llm = OllamaLLM(model="llama3", base_url="http://localhost:11434")
        llm._client = instance
        result = llm.invoke([{"role": "user", "content": "hello"}])

    assert result == "SELECT 1"
