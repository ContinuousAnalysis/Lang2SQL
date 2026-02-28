from __future__ import annotations

from ...core.exceptions import IntegrationMissingError
from ...core.ports import LLMPort

try:
    import anthropic as _anthropic
except ImportError:
    _anthropic = None  # type: ignore[assignment]


class AnthropicLLM(LLMPort):
    """LLMPort implementation backed by the Anthropic Messages API."""

    def __init__(
        self, *, model: str, api_key: str | None = None, max_tokens: int = 4096
    ) -> None:
        if _anthropic is None:
            raise IntegrationMissingError(
                "anthropic", hint="pip install anthropic  # or: uv sync"
            )
        self._client = _anthropic.Anthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    def invoke(self, messages: list[dict[str, str]]) -> str:
        system = next((m["content"] for m in messages if m["role"] == "system"), None)
        user_msgs = [m for m in messages if m["role"] != "system"]
        resp = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=system or "",
            messages=user_msgs,
        )
        return resp.content[0].text
