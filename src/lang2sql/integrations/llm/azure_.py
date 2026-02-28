from __future__ import annotations

from ...core.exceptions import IntegrationMissingError
from ...core.ports import LLMPort

try:
    import openai as _openai
except ImportError:
    _openai = None  # type: ignore[assignment]


class AzureOpenAILLM(LLMPort):
    """LLMPort implementation backed by the Azure OpenAI Chat Completions API."""

    def __init__(
        self,
        *,
        azure_deployment: str,
        azure_endpoint: str,
        api_version: str = "2023-07-01-preview",
        api_key: str | None = None,
        max_tokens: int = 4096,
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
        self._max_tokens = max_tokens

    def invoke(self, messages: list[dict[str, str]]) -> str:
        resp = self._client.chat.completions.create(
            model=self._deployment,
            messages=messages,  # type: ignore[arg-type]
            max_tokens=self._max_tokens,
        )
        return resp.choices[0].message.content or ""
