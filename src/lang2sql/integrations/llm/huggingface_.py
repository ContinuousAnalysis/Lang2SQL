from __future__ import annotations

from ...core.exceptions import IntegrationMissingError
from ...core.ports import LLMPort

try:
    from huggingface_hub import InferenceClient as _InferenceClient  # type: ignore[import]
except ImportError:
    _InferenceClient = None  # type: ignore[assignment]


class HuggingFaceLLM(LLMPort):
    """LLMPort implementation backed by the HuggingFace Inference API."""

    def __init__(
        self,
        *,
        repo_id: str | None = None,
        endpoint_url: str | None = None,
        api_token: str | None = None,
    ) -> None:
        if _InferenceClient is None:
            raise IntegrationMissingError(
                "huggingface_hub", hint="pip install huggingface_hub"
            )
        if repo_id is None and endpoint_url is None:
            raise ValueError("Either repo_id or endpoint_url must be provided.")
        self._client = _InferenceClient(
            model=endpoint_url or repo_id,
            token=api_token,
        )

    def invoke(self, messages: list[dict[str, str]]) -> str:
        resp = self._client.chat_completion(messages=messages)  # type: ignore[arg-type]
        return resp.choices[0].message.content or ""
