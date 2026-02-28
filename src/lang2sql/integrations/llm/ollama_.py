from __future__ import annotations

from ...core.exceptions import IntegrationMissingError
from ...core.ports import LLMPort

try:
    import ollama as _ollama  # type: ignore[import]
except ImportError:
    _ollama = None  # type: ignore[assignment]


class OllamaLLM(LLMPort):
    """LLMPort implementation backed by the Ollama chat API."""

    def __init__(
        self,
        *,
        model: str,
        base_url: str = "http://localhost:11434",
    ) -> None:
        if _ollama is None:
            raise IntegrationMissingError("ollama", hint="pip install ollama")
        self._model = model
        self._client = _ollama.Client(host=base_url)

    def invoke(self, messages: list[dict[str, str]]) -> str:
        resp = self._client.chat(
            model=self._model,
            messages=messages,  # type: ignore[arg-type]
        )
        return resp.message.content
