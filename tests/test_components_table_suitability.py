"""Tests for TableSuitabilityEvaluator component."""

from __future__ import annotations

import json

import pytest

from lang2sql.components.gate.table_suitability import TableSuitabilityEvaluator
from lang2sql.core.catalog import CatalogEntry
from lang2sql.core.hooks import MemoryHook


class FakeLLM:
    def __init__(self, response: str):
        self._response = response

    def invoke(self, messages: list[dict]) -> str:
        return self._response


def _catalog() -> list[CatalogEntry]:
    return [
        {
            "name": "orders",
            "description": "주문 테이블",
            "columns": {"order_id": "주문 ID", "amount": "주문 금액", "created_at": "생성일"},
        },
        {
            "name": "users",
            "description": "사용자 테이블",
            "columns": {"user_id": "사용자 ID", "name": "이름"},
        },
    ]


def _suitability_json(results: list[dict]) -> str:
    return json.dumps({"results": results}, ensure_ascii=False)


def test_table_suitability_filters_below_threshold():
    resp = _suitability_json(
        [
            {
                "table_name": "orders",
                "score": 0.9,
                "reason": "핵심 지표 포함",
                "matched_columns": ["amount"],
                "missing_entities": [],
            },
            {
                "table_name": "users",
                "score": 0.1,
                "reason": "관련 없음",
                "matched_columns": [],
                "missing_entities": ["주문 정보"],
            },
        ]
    )
    evaluator = TableSuitabilityEvaluator(llm=FakeLLM(resp), threshold=0.3)
    result = evaluator.run("지난달 주문 금액 합계", _catalog())
    assert len(result) == 1
    assert result[0]["name"] == "orders"


def test_table_suitability_sorted_by_score():
    resp = _suitability_json(
        [
            {
                "table_name": "users",
                "score": 0.5,
                "reason": "부분 매칭",
                "matched_columns": [],
                "missing_entities": [],
            },
            {
                "table_name": "orders",
                "score": 0.9,
                "reason": "완전 매칭",
                "matched_columns": ["amount"],
                "missing_entities": [],
            },
        ]
    )
    evaluator = TableSuitabilityEvaluator(llm=FakeLLM(resp), threshold=0.3)
    result = evaluator.run("주문 금액", _catalog())
    assert result[0]["name"] == "orders"
    assert result[1]["name"] == "users"


def test_table_suitability_empty_result_when_all_below_threshold():
    resp = _suitability_json(
        [
            {"table_name": "orders", "score": 0.1, "reason": "낮은 관련성", "matched_columns": [], "missing_entities": []},
        ]
    )
    evaluator = TableSuitabilityEvaluator(llm=FakeLLM(resp), threshold=0.3)
    result = evaluator.run("관련 없는 질문", _catalog())
    assert result == []


def test_table_suitability_emits_hook_events():
    hook = MemoryHook()
    resp = _suitability_json(
        [{"table_name": "orders", "score": 0.8, "reason": "ok", "matched_columns": [], "missing_entities": []}]
    )
    evaluator = TableSuitabilityEvaluator(llm=FakeLLM(resp), hook=hook)
    evaluator.run("test", _catalog())
    phases = [e.phase for e in hook.events]
    assert "start" in phases
    assert "end" in phases
