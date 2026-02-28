"""Tests for QuestionGate component."""

from __future__ import annotations

import json

import pytest

from lang2sql.components.gate.question_gate import QuestionGate
from lang2sql.core.catalog import GateResult
from lang2sql.core.hooks import MemoryHook


class FakeLLM:
    def __init__(self, response: str):
        self._response = response

    def invoke(self, messages: list[dict]) -> str:
        return self._response


def _gate_json(
    suitable: bool = True,
    reason: str = "SQL로 답변 가능합니다.",
    missing_entities: list | None = None,
    requires_data_science: bool = False,
) -> str:
    return json.dumps(
        {
            "suitable": suitable,
            "reason": reason,
            "missing_entities": missing_entities or [],
            "requires_data_science": requires_data_science,
        },
        ensure_ascii=False,
    )


def test_question_gate_suitable_true():
    llm = FakeLLM(_gate_json(suitable=True, reason="OK"))
    gate = QuestionGate(llm=llm)
    result = gate.run("지난달 주문 수는?")
    assert isinstance(result, GateResult)
    assert result.suitable is True
    assert result.reason == "OK"


def test_question_gate_suitable_false():
    llm = FakeLLM(
        _gate_json(
            suitable=False,
            reason="통계 분석이 필요합니다.",
            requires_data_science=True,
        )
    )
    gate = QuestionGate(llm=llm)
    result = gate.run("이상 탐지 모델을 만들어줘")
    assert result.suitable is False
    assert result.requires_data_science is True


def test_question_gate_with_missing_entities():
    llm = FakeLLM(
        _gate_json(
            suitable=False,
            missing_entities=["기간", "대상 엔터티"],
        )
    )
    gate = QuestionGate(llm=llm)
    result = gate.run("매출을 보여줘")
    assert "기간" in result.missing_entities


def test_question_gate_strips_markdown_json():
    raw = "```json\n" + _gate_json(suitable=True) + "\n```"
    llm = FakeLLM(raw)
    gate = QuestionGate(llm=llm)
    result = gate.run("test")
    assert result.suitable is True


def test_question_gate_emits_hook_events():
    hook = MemoryHook()
    llm = FakeLLM(_gate_json())
    gate = QuestionGate(llm=llm, hook=hook)
    gate.run("test query")
    phases = [e.phase for e in hook.events]
    assert "start" in phases
    assert "end" in phases
