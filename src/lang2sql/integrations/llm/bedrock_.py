from __future__ import annotations

from ...core.exceptions import IntegrationMissingError
from ...core.ports import LLMPort

try:
    import boto3 as _boto3  # type: ignore[import]
except ImportError:
    _boto3 = None  # type: ignore[assignment]


class BedrockLLM(LLMPort):
    """LLMPort implementation backed by the AWS Bedrock Converse API."""

    def __init__(
        self,
        *,
        model: str,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        region_name: str = "us-east-1",
    ) -> None:
        if _boto3 is None:
            raise IntegrationMissingError(
                "boto3", hint="pip install boto3"
            )
        self._model = model
        self._client = _boto3.client(
            "bedrock-runtime",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name,
        )

    def invoke(self, messages: list[dict[str, str]]) -> str:
        system_parts = [m["content"] for m in messages if m["role"] == "system"]
        user_msgs = [m for m in messages if m["role"] != "system"]

        converse_messages = [
            {"role": m["role"], "content": [{"text": m["content"]}]}
            for m in user_msgs
        ]

        kwargs: dict = {"modelId": self._model, "messages": converse_messages}
        if system_parts:
            kwargs["system"] = [{"text": system_parts[0]}]

        resp = self._client.converse(**kwargs)
        return resp["output"]["message"]["content"][0]["text"]
