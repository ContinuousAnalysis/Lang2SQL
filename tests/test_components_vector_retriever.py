"""
Tests for VectorRetriever, CatalogChunker, RecursiveCharacterChunker — 16 cases.

Mock strategy:
- FakeVectorStore + FakeEmbedding for tests that control search results explicitly.
- InMemoryVectorStore + FakeEmbedding for tests that verify actual storage/merge behavior
  (tests 10, from_chunks_add_incremental). FakeVectorStore.search() returns pre-configured
  results, so it cannot catch real storage bugs.
"""

import pytest

from lang2sql.components.retrieval.chunker import CatalogChunker, RecursiveCharacterChunker
from lang2sql.components.retrieval.vector import VectorRetriever
from lang2sql.core.catalog import RetrievalResult
from lang2sql.core.hooks import MemoryHook
from lang2sql.flows.baseline import SequentialFlow
from lang2sql.integrations.vectorstore import InMemoryVectorStore


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeVectorStore:
    """
    Controlled search results for unit tests.
    search() returns whatever was passed to __init__(results=...).
    upsert() implements merge semantics to match InMemoryVectorStore contract.
    Do NOT use for tests that verify storage correctness — use InMemoryVectorStore instead.
    """

    def __init__(self, results=None):
        self._results = results or []
        self.upserted: dict = {}

    def search(self, vector, k):
        return self._results[:k]

    def upsert(self, ids, vectors):
        # merge semantics — consistent with VectorStorePort contract
        for id_, vec in zip(ids, vectors):
            self.upserted[id_] = vec


class FakeEmbedding:
    def embed_query(self, text):
        return [0.0] * 4

    def embed_texts(self, texts):
        return [[0.0] * 4] * len(texts)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

CATALOG = [
    {
        "name": "orders",
        "description": "Order information table",
        "columns": {"order_id": "Unique order ID", "amount": "Order amount"},
    }
]

DOCS = [
    {
        "id": "biz_rules",
        "title": "Revenue Definition",
        "content": "Revenue is defined as net sales excluding returns.",
        "source": "docs/biz_rules.md",
    }
]


def _make_catalog_registry():
    """Registry pre-populated with one catalog chunk."""
    return {
        "orders__0": {
            "chunk_id": "orders__0",
            "text": "orders: Order information table",
            "source_type": "catalog",
            "source_id": "orders",
            "chunk_index": 0,
            "metadata": CATALOG[0],
        }
    }


def _make_doc_registry():
    """Registry pre-populated with one document chunk."""
    return {
        "biz_rules__0": {
            "chunk_id": "biz_rules__0",
            "text": "Revenue Definition: Revenue is defined as net sales.",
            "source_type": "document",
            "source_id": "biz_rules",
            "chunk_index": 0,
            "metadata": {"id": "biz_rules", "title": "Revenue Definition", "source": ""},
        }
    }


# ---------------------------------------------------------------------------
# 1. Catalog chunk deduplication
# ---------------------------------------------------------------------------


def test_catalog_chunk_dedup():
    """Multiple chunks from the same table → only 1 CatalogEntry returned."""
    registry = {
        "orders__0": {
            "chunk_id": "orders__0",
            "text": "orders: Order table",
            "source_type": "catalog",
            "source_id": "orders",
            "chunk_index": 0,
            "metadata": CATALOG[0],
        },
        "orders__col_1": {
            "chunk_id": "orders__col_1",
            "text": "orders columns: order_id amount",
            "source_type": "catalog",
            "source_id": "orders",
            "chunk_index": 1,
            "metadata": CATALOG[0],
        },
    }
    store = FakeVectorStore(results=[("orders__0", 0.9), ("orders__col_1", 0.8)])
    retriever = VectorRetriever(
        vectorstore=store, embedding=FakeEmbedding(), registry=registry
    )
    result = retriever("order amount")

    assert len(result.schemas) == 1
    assert result.schemas[0]["name"] == "orders"


# ---------------------------------------------------------------------------
# 2. Document chunk in context
# ---------------------------------------------------------------------------


def test_document_chunk_in_context():
    """Document chunk appears in RetrievalResult.context."""
    registry = _make_doc_registry()
    store = FakeVectorStore(results=[("biz_rules__0", 0.8)])
    retriever = VectorRetriever(
        vectorstore=store, embedding=FakeEmbedding(), registry=registry
    )
    result = retriever("revenue definition")

    assert len(result.context) == 1
    assert "Revenue" in result.context[0]


# ---------------------------------------------------------------------------
# 3. Empty registry
# ---------------------------------------------------------------------------


def test_empty_registry_returns_empty_result():
    """Empty registry → empty RetrievalResult."""
    store = FakeVectorStore(results=[("orders__0", 0.9)])
    retriever = VectorRetriever(
        vectorstore=store, embedding=FakeEmbedding(), registry={}
    )
    result = retriever("any query")

    assert result.schemas == []
    assert result.context == []


# ---------------------------------------------------------------------------
# 4. Score threshold filtering
# ---------------------------------------------------------------------------


def test_score_threshold_filters_results():
    """Chunks at or below threshold are excluded."""
    registry = _make_catalog_registry()
    store = FakeVectorStore(results=[("orders__0", 0.3)])
    retriever = VectorRetriever(
        vectorstore=store,
        embedding=FakeEmbedding(),
        registry=registry,
        score_threshold=0.3,  # score must be strictly greater than threshold
    )
    result = retriever("orders")

    assert result.schemas == []


# ---------------------------------------------------------------------------
# 5. top_n limits schemas
# ---------------------------------------------------------------------------


def test_top_n_limits_schemas():
    """schemas capped at top_n."""
    registry = {
        f"table_{i}__0": {
            "chunk_id": f"table_{i}__0",
            "text": f"table_{i}",
            "source_type": "catalog",
            "source_id": f"table_{i}",
            "chunk_index": 0,
            "metadata": {"name": f"table_{i}", "description": "", "columns": {}},
        }
        for i in range(10)
    }
    store = FakeVectorStore(
        results=[(f"table_{i}__0", 0.9 - i * 0.05) for i in range(10)]
    )
    retriever = VectorRetriever(
        vectorstore=store, embedding=FakeEmbedding(), registry=registry, top_n=3
    )
    result = retriever("table")

    assert len(result.schemas) <= 3


# ---------------------------------------------------------------------------
# 6. top_n limits context
# ---------------------------------------------------------------------------


def test_top_n_limits_context():
    """context capped at top_n."""
    registry = {
        f"doc_{i}__0": {
            "chunk_id": f"doc_{i}__0",
            "text": f"doc chunk {i}",
            "source_type": "document",
            "source_id": f"doc_{i}",
            "chunk_index": 0,
            "metadata": {"id": f"doc_{i}", "title": "", "source": ""},
        }
        for i in range(10)
    }
    store = FakeVectorStore(
        results=[(f"doc_{i}__0", 0.9 - i * 0.05) for i in range(10)]
    )
    retriever = VectorRetriever(
        vectorstore=store, embedding=FakeEmbedding(), registry=registry, top_n=3
    )
    result = retriever("doc")

    assert len(result.context) <= 3


# ---------------------------------------------------------------------------
# 7. Hook events
# ---------------------------------------------------------------------------


def test_hook_start_end_events():
    """MemoryHook records start/end events + duration_ms."""
    hook = MemoryHook()
    store = FakeVectorStore()
    retriever = VectorRetriever(
        vectorstore=store, embedding=FakeEmbedding(), registry={}, hook=hook
    )
    retriever("test query")

    assert len(hook.events) == 2
    assert hook.events[0].phase == "start"
    assert hook.events[1].phase == "end"
    assert hook.events[1].duration_ms is not None
    assert hook.events[1].duration_ms >= 0.0


# ---------------------------------------------------------------------------
# 8. from_chunks() — catalog chunks populate registry
# ---------------------------------------------------------------------------


def test_from_chunks_catalog_populates_registry():
    """from_chunks(catalog_chunks) populates registry with catalog source_type."""
    chunks = CatalogChunker().split(CATALOG)
    retriever = VectorRetriever.from_chunks(chunks, embedding=FakeEmbedding())

    assert len(retriever._registry) > 0
    for chunk in retriever._registry.values():
        assert chunk["source_type"] == "catalog"
        assert chunk["source_id"] == "orders"


# ---------------------------------------------------------------------------
# 9. from_chunks() — document chunks populate registry
# ---------------------------------------------------------------------------


def test_from_chunks_doc_populates_registry():
    """from_chunks(doc_chunks) populates registry with document source_type."""
    chunks = RecursiveCharacterChunker().split(DOCS)
    retriever = VectorRetriever.from_chunks(chunks, embedding=FakeEmbedding())

    assert len(retriever._registry) > 0
    for chunk in retriever._registry.values():
        assert chunk["source_type"] == "document"
        assert chunk["source_id"] == "biz_rules"


# ---------------------------------------------------------------------------
# 10. InMemoryVectorStore merge — catalog survives after doc chunks added
# ---------------------------------------------------------------------------


def test_from_chunks_preserves_catalog_after_doc_run():
    """
    catalog vectors survive when doc chunks are combined.
    Uses InMemoryVectorStore to verify real merge behavior.
    """
    store = InMemoryVectorStore()
    catalog_chunks = CatalogChunker().split(CATALOG)
    retriever = VectorRetriever.from_chunks(
        catalog_chunks, embedding=FakeEmbedding(), vectorstore=store
    )
    catalog_chunk_ids = set(retriever._registry.keys())
    assert len(catalog_chunk_ids) > 0

    doc_chunks = RecursiveCharacterChunker().split(DOCS)
    retriever.add(doc_chunks)

    for chunk_id in catalog_chunk_ids:
        assert chunk_id in store._store, f"catalog chunk '{chunk_id}' lost after add()"


# ---------------------------------------------------------------------------
# 11. CatalogChunker — column groups
# ---------------------------------------------------------------------------


def test_catalog_chunker_column_groups():
    """25 columns → CatalogChunker (max 20) produces at least 2 chunks beyond header."""
    entry = {
        "name": "big_table",
        "description": "Large table",
        "columns": {f"col_{i}": f"column {i}" for i in range(25)},
    }
    chunker = CatalogChunker(max_columns_per_chunk=20)
    chunks = chunker.chunk(entry)

    # chunk 0 = header, chunk 1 = first 20 cols, chunk 2 = remaining 5 cols
    assert len(chunks) >= 3
    assert chunks[0]["chunk_id"] == "big_table__0"
    assert all(c["source_type"] == "catalog" for c in chunks)
    assert all(c["metadata"]["name"] == "big_table" for c in chunks)


# ---------------------------------------------------------------------------
# 12. RecursiveCharacterChunker — respects chunk_size
# ---------------------------------------------------------------------------


def test_recursive_chunker_respects_chunk_size():
    """Text exceeding chunk_size is split into multiple chunks."""
    chunker = RecursiveCharacterChunker(chunk_size=50, chunk_overlap=0)
    doc = {
        "id": "doc1",
        "title": "",
        "content": "A" * 50 + "\n\n" + "B" * 50,
        "source": "",
    }
    chunks = chunker.chunk(doc)

    assert len(chunks) >= 2
    for chunk in chunks:
        # title prefix is empty so raw text length should respect chunk_size
        assert len(chunk["text"]) <= 50 + 10  # small tolerance for separator


# ---------------------------------------------------------------------------
# 13. RecursiveCharacterChunker — overlap
# ---------------------------------------------------------------------------


def test_recursive_chunker_overlap():
    """Second chunk contains tail characters of the first chunk."""
    overlap = 20
    chunker = RecursiveCharacterChunker(chunk_size=40, chunk_overlap=overlap)
    long_content = "Hello world this is a test. " * 10
    doc = {"id": "d1", "title": "", "content": long_content, "source": ""}
    chunks = chunker.chunk(doc)

    if len(chunks) >= 2:
        tail_of_first = chunks[0]["text"][-overlap:]
        assert tail_of_first in chunks[1]["text"]


# ---------------------------------------------------------------------------
# 14. from_sources() — builds retriever with non-empty registry
# ---------------------------------------------------------------------------


def test_from_sources_builds_retriever():
    """from_sources() returns a VectorRetriever with non-empty registry."""
    retriever = VectorRetriever.from_sources(
        catalog=CATALOG,
        embedding=FakeEmbedding(),
    )

    assert isinstance(retriever, VectorRetriever)
    assert len(retriever._registry) > 0


# ---------------------------------------------------------------------------
# 15. from_sources() + add() — incremental indexing
# ---------------------------------------------------------------------------


def test_from_sources_add_incremental():
    """retriever.add(chunks) adds chunks without losing existing catalog chunks."""
    retriever = VectorRetriever.from_sources(
        catalog=CATALOG,
        embedding=FakeEmbedding(),
    )
    initial_ids = set(retriever._registry.keys())
    assert len(initial_ids) > 0

    doc_chunks = RecursiveCharacterChunker().split(DOCS)
    retriever.add(doc_chunks)

    final_ids = set(retriever._registry.keys())
    # new doc chunks were added
    assert len(final_ids) > len(initial_ids)
    # original catalog chunks are still present
    for chunk_id in initial_ids:
        assert chunk_id in final_ids, f"catalog chunk '{chunk_id}' lost after add()"


# ---------------------------------------------------------------------------
# 16. from_chunks() — empty chunks → empty result
# ---------------------------------------------------------------------------


def test_from_chunks_empty():
    """from_chunks([]) → retriever with empty registry returns empty result."""
    retriever = VectorRetriever.from_chunks([], embedding=FakeEmbedding())

    assert retriever._registry == {}
    result = retriever("any query")
    assert result.schemas == []
    assert result.context == []


# ---------------------------------------------------------------------------
# 17. from_chunks() — mixed catalog + doc chunks
# ---------------------------------------------------------------------------


def test_from_chunks_mixed_catalog_and_docs():
    """from_chunks with catalog + doc chunks → both source_types in registry."""
    chunks = CatalogChunker().split(CATALOG) + RecursiveCharacterChunker().split(DOCS)
    retriever = VectorRetriever.from_chunks(chunks, embedding=FakeEmbedding())

    source_types = {c["source_type"] for c in retriever._registry.values()}
    assert "catalog" in source_types
    assert "document" in source_types


# ---------------------------------------------------------------------------
# 18. from_chunks() + add() — incremental after from_chunks
# ---------------------------------------------------------------------------


def test_from_chunks_add_incremental():
    """from_chunks() followed by add(more_chunks) preserves original chunks."""
    store = InMemoryVectorStore()
    catalog_chunks = CatalogChunker().split(CATALOG)
    retriever = VectorRetriever.from_chunks(
        catalog_chunks, embedding=FakeEmbedding(), vectorstore=store
    )
    initial_ids = set(retriever._registry.keys())

    doc_chunks = RecursiveCharacterChunker().split(DOCS)
    retriever.add(doc_chunks)

    final_ids = set(retriever._registry.keys())
    assert len(final_ids) > len(initial_ids)
    for chunk_id in initial_ids:
        assert chunk_id in final_ids, f"chunk '{chunk_id}' lost after add()"


# ---------------------------------------------------------------------------
# 19. CatalogChunker.split() — batch convenience method
# ---------------------------------------------------------------------------


def test_catalog_chunker_split_batch():
    """CatalogChunker.split(catalog) returns same chunks as calling chunk() per entry."""
    chunker = CatalogChunker()
    by_split = chunker.split(CATALOG)
    by_chunk = [c for entry in CATALOG for c in chunker.chunk(entry)]

    assert [c["chunk_id"] for c in by_split] == [c["chunk_id"] for c in by_chunk]
