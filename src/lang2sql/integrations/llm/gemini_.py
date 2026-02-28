from __future__ import annotations

from ...core.exceptions import IntegrationMissingError
from ...core.ports import LLMPort

try:
    import google.generativeai as _genai  # type: ignore[import]
except ImportError:
    _genai = None  # type: ignore[assignment]


class GeminiLLM(LLMPort):
    """LLMPort implementation backed by the Google Gemini Generative AI API."""

    def __init__(
        self,
        *,
        model: str,
        api_key: str | None = None,
    ) -> None:
        if _genai is None:
            raise IntegrationMissingError(
                "google-generativeai",
                hint="pip install google-generativeai",
            )
        if api_key:
            _genai.configure(api_key=api_key)
        self._model_name = model

    def invoke(self, messages: list[dict[str, str]]) -> str:
        system_parts = [m["content"] for m in messages if m["role"] == "system"]
        system_instruction = system_parts[0] if system_parts else None

        contents = []
        for m in messages:
            if m["role"] == "system":
                continue
            role = "model" if m["role"] == "assistant" else "user"
            contents.append({"role": role, "parts": [m["content"]]})

        model = _genai.GenerativeModel(
            model_name=self._model_name,
            system_instruction=system_instruction,
        )
        response = model.generate_content(contents)
        return response.text
