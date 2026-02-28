from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from ...core.base import BaseComponent
from ...core.catalog import CatalogEntry, TableScore
from ...core.hooks import TraceHook
from ...core.ports import LLMPort

_PROMPT_PATH = Path(__file__).parent / "prompts" / "table_suitability.md"


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8").strip()


def _parse_json(text: str) -> dict:
    match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if match:
        text = match.group(1).strip()
    return json.loads(text)


class TableSuitabilityEvaluator(BaseComponent):
    """검색된 테이블을 질문 관련도순으로 필터링한다."""

    def __init__(
        self,
        *,
        llm: LLMPort,
        threshold: float = 0.3,
        name: Optional[str] = None,
        hook: Optional[TraceHook] = None,
    ) -> None:
        super().__init__(name=name or "TableSuitabilityEvaluator", hook=hook)
        self._llm = llm
        self._threshold = threshold
        self._system_prompt = _load_prompt()

    def _run(self, query: str, schemas: list[CatalogEntry]) -> list[CatalogEntry]:
        # 테이블을 {table_name: {col: desc, ...}} 구조로 직렬화
        tables_map: dict[str, dict] = {}
        for entry in schemas:
            name = entry.get("name", "")
            cols = entry.get("columns", {})
            desc = entry.get("description", "")
            tables_map[name] = {"table_description": desc, **cols}

        tables_json = json.dumps(tables_map, ensure_ascii=False)
        user_content = (
            self._system_prompt
            .replace("{question}", query)
            .replace("{tables}", tables_json)
        )
        messages = [{"role": "user", "content": user_content}]
        response = self._llm.invoke(messages)
        data = _parse_json(response)

        results: list[TableScore] = [
            TableScore(
                table_name=r["table_name"],
                score=float(r.get("score", 0.0)),
                reason=str(r.get("reason", "")),
                matched_columns=list(r.get("matched_columns", [])),
                missing_entities=list(r.get("missing_entities", [])),
            )
            for r in data.get("results", [])
        ]

        # threshold 이상인 테이블만 score 내림차순으로 필터
        passing = {r.table_name for r in results if r.score >= self._threshold}
        filtered = [e for e in schemas if e.get("name", "") in passing]

        # score 내림차순 정렬
        score_map = {r.table_name: r.score for r in results}
        filtered.sort(key=lambda e: score_map.get(e.get("name", ""), 0.0), reverse=True)
        return filtered
