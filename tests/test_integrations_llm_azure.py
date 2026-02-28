"""Tests for AzureOpenAILLM integration."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

openai = pytest.importorskip("openai", reason="openai not installed")

from lang2sql.integrations.llm.azure_ import AzureOpenAILLM


def _make_llm() -> AzureOpenAILLM:
    return AzureOpenAILLM(
        azure_deployment="gpt-4o",
        azure_endpoint="https://test.openai.azure.com/",
        api_key="test-key",
    )


def test_azure_llm_invoke_returns_string():
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = "SELECT 1"

    with patch("openai.AzureOpenAI") as MockClient:
        instance = MockClient.return_value
        instance.chat.completions.create.return_value = mock_resp

        llm = _make_llm()
        llm._client = instance
        result = llm.invoke([{"role": "user", "content": "hello"}])

    assert result == "SELECT 1"


def test_azure_llm_missing_dependency_raises():
    import sys

    with patch.dict(sys.modules, {"openai": None}):
        # Re-import to trigger the ImportError guard
        import importlib

        import lang2sql.integrations.llm.azure_ as mod

        importlib.reload(mod)
        with pytest.raises(Exception):
            mod.AzureOpenAILLM(
                azure_deployment="x",
                azure_endpoint="https://x.openai.azure.com/",
            )
        # Reload back
        importlib.reload(mod)
