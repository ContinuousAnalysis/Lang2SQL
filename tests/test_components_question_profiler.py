"""Tests for QuestionProfiler component."""

from __future__ import annotations

import json

import pytest

from lang2sql.components.enrichment.question_profiler import QuestionProfiler
from lang2sql.core.catalog import QuestionProfile
from lang2sql.core.hooks import MemoryHook


class FakeLLM:
    def __init__(self, response: str):
        self._response = response

    def invoke(self, messages: list[dict]) -> str:
        return self._response


def _profile_json(**kwargs) -> str:
    defaults = {
        "is_timeseries": False,
        "is_aggregation": True,
        "has_filter": True,
        "is_grouped": False,
        "has_ranking": False,
        "has_temporal_comparison": False,
        "intent_type": "lookup",
    }
    defaults.update(kwargs)
    return json.dumps(defaults)


def test_question_profiler_returns_profile():
    llm = FakeLLM(_profile_json(is_aggregation=True, has_filter=True))
    profiler = QuestionProfiler(llm=llm)
    result = profiler.run("지난달 주문 수")
    assert isinstance(result, QuestionProfile)
    assert result.is_aggregation is True
    assert result.has_filter is True


def test_question_profiler_timeseries():
    llm = FakeLLM(_profile_json(is_timeseries=True, intent_type="trend"))
    profiler = QuestionProfiler(llm=llm)
    result = profiler.run("월별 매출 추이")
    assert result.is_timeseries is True
    assert result.intent_type == "trend"


def test_question_profiler_invalid_intent_type_falls_back_to_lookup():
    llm = FakeLLM(_profile_json(intent_type="invalid_type"))
    profiler = QuestionProfiler(llm=llm)
    result = profiler.run("test")
    assert result.intent_type == "lookup"


def test_question_profiler_strips_markdown_json():
    raw = "```json\n" + _profile_json() + "\n```"
    llm = FakeLLM(raw)
    profiler = QuestionProfiler(llm=llm)
    result = profiler.run("test")
    assert isinstance(result, QuestionProfile)


def test_question_profiler_emits_hook_events():
    hook = MemoryHook()
    llm = FakeLLM(_profile_json())
    profiler = QuestionProfiler(llm=llm, hook=hook)
    profiler.run("test")
    phases = [e.phase for e in hook.events]
    assert "start" in phases
    assert "end" in phases
