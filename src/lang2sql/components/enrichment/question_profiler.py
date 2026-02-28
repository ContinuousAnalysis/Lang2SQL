from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from ...core.base import BaseComponent
from ...core.catalog import QuestionProfile
from ...core.hooks import TraceHook
from ...core.ports import LLMPort

_PROMPT_PATH = Path(__file__).parent / "prompts" / "question_profiler.md"

_VALID_INTENT_TYPES = {"trend", "lookup", "comparison", "distribution"}


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8").strip()


def _parse_json(text: str) -> dict:
    match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if match:
        text = match.group(1).strip()
    return json.loads(text)


class QuestionProfiler(BaseComponent):
    """질문에서 구조화된 특성(시계열, 집계, 필터 등)을 추출한다."""

    def __init__(
        self,
        *,
        llm: LLMPort,
        name: Optional[str] = None,
        hook: Optional[TraceHook] = None,
    ) -> None:
        super().__init__(name=name or "QuestionProfiler", hook=hook)
        self._llm = llm
        self._system_prompt = _load_prompt()

    def _run(self, query: str) -> QuestionProfile:
        user_content = self._system_prompt.replace("{question}", query)
        messages = [{"role": "user", "content": user_content}]
        response = self._llm.invoke(messages)
        data = _parse_json(response)

        intent_type = str(data.get("intent_type", "lookup"))
        if intent_type not in _VALID_INTENT_TYPES:
            intent_type = "lookup"

        return QuestionProfile(
            is_timeseries=bool(data.get("is_timeseries", False)),
            is_aggregation=bool(data.get("is_aggregation", False)),
            has_filter=bool(data.get("has_filter", False)),
            is_grouped=bool(data.get("is_grouped", False)),
            has_ranking=bool(data.get("has_ranking", False)),
            has_temporal_comparison=bool(data.get("has_temporal_comparison", False)),
            intent_type=intent_type,
        )
