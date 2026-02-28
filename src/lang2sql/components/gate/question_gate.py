from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from ...core.base import BaseComponent
from ...core.catalog import GateResult
from ...core.hooks import TraceHook
from ...core.ports import LLMPort

_PROMPT_PATH = Path(__file__).parent / "prompts" / "question_gate.md"


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8").strip()


def _parse_json(text: str) -> dict:
    """LLM 응답에서 JSON을 추출한다. 마크다운 코드블록을 자동으로 제거한다."""
    # ```json ... ``` 또는 ``` ... ``` 블록 제거
    match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if match:
        text = match.group(1).strip()
    return json.loads(text)


class QuestionGate(BaseComponent):
    """질문이 SQL로 답변 가능한지 판별한다."""

    def __init__(
        self,
        *,
        llm: LLMPort,
        name: Optional[str] = None,
        hook: Optional[TraceHook] = None,
    ) -> None:
        super().__init__(name=name or "QuestionGate", hook=hook)
        self._llm = llm
        self._system_prompt = _load_prompt()

    def _run(self, query: str) -> GateResult:
        user_content = self._system_prompt.replace("{question}", query)
        messages = [
            {"role": "user", "content": user_content},
        ]
        response = self._llm.invoke(messages)
        data = _parse_json(response)
        return GateResult(
            suitable=bool(data.get("suitable", True)),
            reason=str(data.get("reason", "")),
            missing_entities=list(data.get("missing_entities", [])),
            requires_data_science=bool(data.get("requires_data_science", False)),
        )
