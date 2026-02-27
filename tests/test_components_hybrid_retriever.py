"""
Tests for HybridRetriever and HybridNL2SQL — 8 cases.

SmartFakeEmbedding maps marker keywords in text to orthogonal unit vectors:
  - "bothdim"  → [0.7071, 0.0, 0.7071, 0.0]  (found by both BM25 and vector)
  - "kwcommon" → [0.0,    1.0, 0.0,    0.0]  (positive BM25, zero cosine with query)
  - "vdimonly" → [0.0,    0.0, 1.0,    0.0]  (zero BM25, positive cosine with query)
  - other      → [0.0,    0.0, 0.0,    1.0]

Query "BOTHDIM KWCOMMON" embeds to [0.7071, 0, 0.7071, 0] (has "bothdim").
  - both_table  (bothdim): cosine 1.0 → in vector ✓ ; BM25 matches "bothdim"+"kwcommon" ✓
  - kwonly_table(kwcommon): cosine 0.0 → NOT in vector ✓ ; BM25 matches "kwcommon" ✓
  - veconly_table(vdimonly): cosine 0.707 → in vector ✓ ; BM25 score 0 → not returned ✓
"""

from __future__ import annotations

import pytest

from lang2sql.components.retrieval.hybrid import HybridRetriever
from lang2sql.core.catalog import RetrievalResult
from lang2sql.core.hooks import MemoryHook
from lang2sql.flows.hybrid import HybridNL2SQL

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeEmbedding:
    """Uniform embedding — all texts and queries map to the same unit vector."""

    def embed_query(self, text: str) -> list[float]:
        return [0.5, 0.5, 0.5, 0.5]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[0.5, 0.5, 0.5, 0.5]] * len(texts)


class SmartFakeEmbedding:
    """
    Marker-based deterministic embedding for controlled retrieval testing.

    Marker priority (first match wins):
      "bothdim"  → [√½, 0, √½, 0]  — high cosine with query on dims 0 and 2
      "vdimonly" → [0, 0, 1, 0]    — matches query dim 2 only
      "kwcommon" → [0, 1, 0, 0]    — orthogonal to query → cosine 0.0 (excluded)
      else       → [0, 0, 0, 1]    — orthogonal to query → cosine 0.0 (excluded)

    Query "BOTHDIM KWCOMMON" has "bothdim" → embeds to [√½, 0, √½, 0].
    """

    _SQRT2_INV = 2.0**-0.5  # ≈ 0.7071

    def _embed(self, text: str) -> list[float]:
        t = text.lower()
        if "bothdim" in t:
            return [self._SQRT2_INV, 0.0, self._SQRT2_INV, 0.0]
        if "vdimonly" in t:
            return [0.0, 0.0, 1.0, 0.0]
        if "kwcommon" in t:
            return [0.0, 1.0, 0.0, 0.0]
        return [0.0, 0.0, 0.0, 1.0]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]


class FakeLLM:
    def __init__(self, response: str = "```sql\nSELECT COUNT(*) FROM orders\n```"):
        self._response = response

    def invoke(self, messages: list[dict]) -> str:
        return self._response


class FakeDB:
    def __init__(self, rows: list[dict] | None = None):
        self._rows = rows if rows is not None else [{"count": 1}]

    def execute(self, sql: str) -> list[dict]:
        return self._rows


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

CATALOG_SIMPLE = [
    {"name": "orders", "description": "order records", "columns": {"id": "pk"}},
    {"name": "customers", "description": "customer data", "columns": {"id": "pk"}},
]

# Three-table catalog designed for deterministic BM25 vs vector split:
#   - both_table:   found by BOTH BM25 ("bothdim"+"kwcommon" in description) AND vector (cosine 1.0)
#   - kwonly_table: found by BM25 only   ("kwcommon" matches query token)      → vector cosine 0.0
#   - veconly_table:found by vector only  (vdimonly → cosine 0.707)             → BM25 score 0
CATALOG_HYBRID = [
    {
        "name": "both_table",
        "description": "BOTHDIM KWCOMMON data",
        "columns": {"id": "pk"},
    },
    {
        "name": "kwonly_table",
        "description": "KWCOMMON unique info",
        "columns": {"id": "pk"},
    },
    {
        "name": "veconly_table",
        "description": "VDIMONLY specific",
        "columns": {"id": "pk"},
    },
]

DOCS = [
    {
        "id": "revenue_doc",
        "title": "Revenue Rules",
        "content": "Revenue is net sales minus returns.",
        "source": "docs/revenue.md",
    }
]

# Query that:
#   - BM25-matches "both_table" (has "bothdim" and "kwcommon") and "kwonly_table" (has "kwcommon")
#   - Embeds to [√½, 0, √½, 0] via SmartFakeEmbedding (triggered by "bothdim")
#   - cosine("both_table") = 1.0, cosine("kwonly_table") = 0.0, cosine("veconly_table") = 0.707
HYBRID_QUERY = "BOTHDIM KWCOMMON"


# ---------------------------------------------------------------------------
# 1. Return type is RetrievalResult
# ---------------------------------------------------------------------------


def test_hybrid_returns_retrieval_result():
    retriever = HybridRetriever(
        catalog=CATALOG_SIMPLE,
        embedding=FakeEmbedding(),
    )
    result = retriever("orders")
    assert isinstance(result, RetrievalResult)
    assert isinstance(result.schemas, list)
    assert isinstance(result.context, list)


# ---------------------------------------------------------------------------
# 2. RRF combines both retrievers — all three match types present
# ---------------------------------------------------------------------------


def test_hybrid_rrf_combines_both_retrievers():
    """keyword-only, vector-only, and both-matched tables must all appear in results."""
    retriever = HybridRetriever(
        catalog=CATALOG_HYBRID,
        embedding=SmartFakeEmbedding(),
        top_n=3,
    )
    result = retriever(HYBRID_QUERY)
    names = {s["name"] for s in result.schemas}

    assert "both_table" in names, "both_table (found by both) must be in results"
    assert "kwonly_table" in names, "kwonly_table (BM25-only) must be in results"
    assert "veconly_table" in names, "veconly_table (vector-only) must be in results"


# ---------------------------------------------------------------------------
# 3. Tables found by both retrievers rank higher than single-retriever tables
# ---------------------------------------------------------------------------


def test_hybrid_rrf_ranks_overlap_higher():
    """A table found by both retrievers must rank higher than any single-retriever table."""
    retriever = HybridRetriever(
        catalog=CATALOG_HYBRID,
        embedding=SmartFakeEmbedding(),
        top_n=3,
    )
    result = retriever(HYBRID_QUERY)
    names = [s["name"] for s in result.schemas]

    assert names[0] == "both_table", "both_table (highest RRF score) must be rank 1"
    assert names.index("both_table") < names.index("kwonly_table")
    assert names.index("both_table") < names.index("veconly_table")


# ---------------------------------------------------------------------------
# 4. top_n limits schemas count
# ---------------------------------------------------------------------------


def test_hybrid_top_n_limits_schemas():
    retriever = HybridRetriever(
        catalog=CATALOG_HYBRID,
        embedding=SmartFakeEmbedding(),
        top_n=2,
    )
    result = retriever(HYBRID_QUERY)
    assert len(result.schemas) <= 2


# ---------------------------------------------------------------------------
# 5. context comes only from VectorRetriever
# ---------------------------------------------------------------------------


def test_hybrid_context_from_vector():
    """Context must come from VectorRetriever only (document chunk text)."""
    retriever = HybridRetriever(
        catalog=CATALOG_SIMPLE,
        embedding=FakeEmbedding(),
        documents=DOCS,
        top_n=5,
    )
    result = retriever("revenue rules")

    assert isinstance(result.context, list)
    assert len(result.context) > 0, "document text must appear in context"
    assert any("Revenue" in c for c in result.context)


# ---------------------------------------------------------------------------
# 6. Hook records start/end events for HybridRetriever itself
# ---------------------------------------------------------------------------


def test_hybrid_hook_events():
    hook = MemoryHook()
    retriever = HybridRetriever(
        catalog=CATALOG_SIMPLE,
        embedding=FakeEmbedding(),
        hook=hook,
    )
    retriever("orders")

    hybrid_events = [e for e in hook.snapshot() if e.component == "HybridRetriever"]
    assert any(e.phase == "start" for e in hybrid_events)
    assert any(e.phase == "end" for e in hybrid_events)
    end_event = next(e for e in hybrid_events if e.phase == "end")
    assert end_event.duration_ms is not None
    assert end_event.duration_ms >= 0.0


# ---------------------------------------------------------------------------
# 7. HybridNL2SQL end-to-end pipeline
# ---------------------------------------------------------------------------


def test_hybrid_nl2sql_pipeline():
    """HybridNL2SQL end-to-end with FakeLLM + FakeDB."""
    rows = [{"count": 7}]
    pipeline = HybridNL2SQL(
        catalog=CATALOG_SIMPLE,
        llm=FakeLLM(),
        db=FakeDB(rows),
        embedding=FakeEmbedding(),
    )
    result = pipeline.run("How many orders last month?")
    assert result == rows


# ---------------------------------------------------------------------------
# 8. _rrf_merge deduplication — same table in both → score combined, no duplicate
# ---------------------------------------------------------------------------


def test_rrf_merge_deduplication():
    """Same table in both retrievers → scores combined, no duplicate in results."""
    retriever = HybridRetriever(
        catalog=CATALOG_SIMPLE,
        embedding=FakeEmbedding(),
    )
    entry = {"name": "orders", "description": "order data", "columns": {}}

    merged = retriever._rrf_merge([entry], [entry])

    assert len(merged) == 1, "duplicate table must appear only once"
    assert merged[0]["name"] == "orders"
