"""Tests for ContextEnricher component."""

from __future__ import annotations

import pytest

from lang2sql.components.enrichment.context_enricher import ContextEnricher
from lang2sql.core.catalog import CatalogEntry, QuestionProfile
from lang2sql.core.hooks import MemoryHook


class FakeLLM:
    def __init__(self, response: str = "지난달(2024-03) 주문 건수를 COUNT하는 쿼리"):
        self._response = response

    def invoke(self, messages: list[dict]) -> str:
        return self._response


def _catalog() -> list[CatalogEntry]:
    return [
        {
            "name": "orders",
            "description": "주문 테이블",
            "columns": {"order_id": "주문 ID", "amount": "주문 금액", "created_at": "생성일"},
        }
    ]


def _profile(is_aggregation: bool = True) -> QuestionProfile:
    return QuestionProfile(
        is_aggregation=is_aggregation,
        has_filter=True,
        intent_type="lookup",
    )


def test_context_enricher_returns_string():
    llm = FakeLLM("enriched question text")
    enricher = ContextEnricher(llm=llm)
    result = enricher.run("주문 수", _catalog(), _profile())
    assert isinstance(result, str)
    assert result == "enriched question text"


def test_context_enricher_trims_whitespace():
    llm = FakeLLM("  enriched  ")
    enricher = ContextEnricher(llm=llm)
    result = enricher.run("test", _catalog(), _profile())
    assert result == "enriched"


def test_context_enricher_emits_hook_events():
    hook = MemoryHook()
    llm = FakeLLM("enriched")
    enricher = ContextEnricher(llm=llm, hook=hook)
    enricher.run("test", _catalog(), _profile())
    phases = [e.phase for e in hook.events]
    assert "start" in phases
    assert "end" in phases


def test_context_enricher_passes_profile_to_llm():
    received_messages = []

    class CaptureLLM:
        def invoke(self, messages: list[dict]) -> str:
            received_messages.extend(messages)
            return "ok"

    profiler = QuestionProfile(is_timeseries=True, intent_type="trend")
    enricher = ContextEnricher(llm=CaptureLLM())
    enricher.run("월별 추이", _catalog(), profiler)
    assert received_messages
    # profile JSON should appear in the message content
    assert "is_timeseries" in received_messages[0]["content"]
