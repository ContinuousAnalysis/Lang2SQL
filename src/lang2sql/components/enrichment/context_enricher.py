from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Optional

from ...core.base import BaseComponent
from ...core.catalog import CatalogEntry, QuestionProfile
from ...core.hooks import TraceHook
from ...core.ports import LLMPort

_PROMPT_PATH = Path(__file__).parent / "prompts" / "context_enricher.md"


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8").strip()


class ContextEnricher(BaseComponent):
    """질문 프로파일 + 스키마 메타데이터로 질문을 보강한다."""

    def __init__(
        self,
        *,
        llm: LLMPort,
        name: Optional[str] = None,
        hook: Optional[TraceHook] = None,
    ) -> None:
        super().__init__(name=name or "ContextEnricher", hook=hook)
        self._llm = llm
        self._system_prompt = _load_prompt()

    def _run(
        self,
        query: str,
        schemas: list[CatalogEntry],
        profile: QuestionProfile,
    ) -> str:
        profiles_json = json.dumps(dataclasses.asdict(profile), ensure_ascii=False)

        tables_map: dict[str, dict] = {
            entry.get("name", ""): {
                "description": entry.get("description", ""),
                "columns": entry.get("columns", {}),
            }
            for entry in schemas
        }
        tables_json = json.dumps(tables_map, ensure_ascii=False)

        user_content = (
            self._system_prompt
            .replace("{profiles}", profiles_json)
            .replace("{related_tables}", tables_json)
            .replace("{refined_question}", query)
        )
        messages = [{"role": "user", "content": user_content}]
        return self._llm.invoke(messages).strip()
