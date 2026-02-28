"""Tests for EnrichedNL2SQL flow."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from lang2sql.core.catalog import CatalogEntry
from lang2sql.core.exceptions import ContractError
from lang2sql.core.hooks import MemoryHook
from lang2sql.flows.enriched_nl2sql import EnrichedNL2SQL

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeLLM:
    """Configurable fake LLM that cycles through responses."""

    def __init__(self, responses: list[str]):
        self._responses = list(responses)
        self._idx = 0

    def invoke(self, messages: list[dict]) -> str:
        resp = self._responses[self._idx % len(self._responses)]
        self._idx += 1
        return resp


class FakeDB:
    def execute(self, sql: str) -> list[dict]:
        return [{"count": 42}]


class FakeEmbedding:
    def embed_query(self, text: str) -> list[float]:
        return [0.1, 0.2, 0.3]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3] for _ in texts]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _gate_json(suitable: bool = True) -> str:
    return json.dumps(
        {
            "suitable": suitable,
            "reason": "ok" if suitable else "not suitable",
            "missing_entities": [],
            "requires_data_science": False,
        }
    )


def _suitability_json(table_names: list[str], score: float = 0.9) -> str:
    return json.dumps(
        {
            "results": [
                {
                    "table_name": name,
                    "score": score,
                    "reason": "ok",
                    "matched_columns": [],
                    "missing_entities": [],
                }
                for name in table_names
            ]
        }
    )


def _profile_json() -> str:
    return json.dumps(
        {
            "is_timeseries": False,
            "is_aggregation": True,
            "has_filter": False,
            "is_grouped": False,
            "has_ranking": False,
            "has_temporal_comparison": False,
            "intent_type": "lookup",
        }
    )


def _catalog() -> list[CatalogEntry]:
    return [
        {
            "name": "orders",
            "description": "주문 테이블",
            "columns": {"order_id": "ID", "amount": "금액", "created_at": "생성일"},
        }
    ]


def _make_pipeline(gate_enabled: bool = True) -> EnrichedNL2SQL:
    # LLM response order:
    # 1. QuestionGate  → gate JSON
    # 2. TableSuitabilityEvaluator → suitability JSON
    # 3. QuestionProfiler → profile JSON
    # 4. ContextEnricher → enriched string
    # 5. SQLGenerator → sql block
    llm = FakeLLM(
        [
            _gate_json(suitable=True),
            _suitability_json(["orders"]),
            _profile_json(),
            "지난달 주문 건수를 구합니다",
            "```sql\nSELECT COUNT(*) FROM orders\n```",
        ]
    )
    return EnrichedNL2SQL(
        catalog=_catalog(),
        llm=llm,
        db=FakeDB(),
        embedding=FakeEmbedding(),
        db_dialect="sqlite",
        gate_enabled=gate_enabled,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_enriched_nl2sql_full_pipeline_returns_rows():
    pipeline = _make_pipeline()
    rows = pipeline.run("지난달 주문 건수")
    assert rows == [{"count": 42}]


def test_enriched_nl2sql_gate_disabled_skips_gate():
    # With gate disabled, LLM responses shift by one
    llm = FakeLLM(
        [
            _suitability_json(["orders"]),
            _profile_json(),
            "enriched query",
            "```sql\nSELECT COUNT(*) FROM orders\n```",
        ]
    )
    pipeline = EnrichedNL2SQL(
        catalog=_catalog(),
        llm=llm,
        db=FakeDB(),
        embedding=FakeEmbedding(),
        gate_enabled=False,
    )
    rows = pipeline.run("주문 건수")
    assert rows == [{"count": 42}]


def test_enriched_nl2sql_gate_raises_contract_error_when_not_suitable():
    llm = FakeLLM([_gate_json(suitable=False)])
    pipeline = EnrichedNL2SQL(
        catalog=_catalog(),
        llm=llm,
        db=FakeDB(),
        embedding=FakeEmbedding(),
        gate_enabled=True,
    )
    with pytest.raises(ContractError):
        pipeline.run("통계 모델을 만들어줘")


def test_enriched_nl2sql_emits_hook_events():
    hook = MemoryHook()
    llm = FakeLLM(
        [
            _gate_json(suitable=True),
            _suitability_json(["orders"]),
            _profile_json(),
            "enriched",
            "```sql\nSELECT COUNT(*) FROM orders\n```",
        ]
    )
    pipeline = EnrichedNL2SQL(
        catalog=_catalog(),
        llm=llm,
        db=FakeDB(),
        embedding=FakeEmbedding(),
        gate_enabled=True,
        hook=hook,
    )
    pipeline.run("주문 건수")
    # At minimum, the flow itself emits start/end
    assert len(hook.events) > 0
