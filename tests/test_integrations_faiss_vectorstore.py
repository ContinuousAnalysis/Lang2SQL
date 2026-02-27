"""
FAISSVectorStore integration tests.

All tests are auto-skipped when faiss-cpu is not installed.
"""
import pytest

faiss = pytest.importorskip("faiss")  # skip entire module if not installed

import tempfile
import os

from lang2sql.integrations.vectorstore.faiss_ import FAISSVectorStore


# ── helpers ──────────────────────────────────────────────────────────────────


def _ortho_vectors() -> list[tuple[str, list[float]]]:
    """4 orthogonal unit vectors for deterministic cosine tests."""
    return [
        ("a", [1.0, 0.0, 0.0, 0.0]),
        ("b", [0.0, 1.0, 0.0, 0.0]),
        ("c", [0.0, 0.0, 1.0, 0.0]),
        ("d", [0.0, 0.0, 0.0, 1.0]),
    ]


@pytest.fixture
def store() -> FAISSVectorStore:
    return FAISSVectorStore()


def _populate(store: FAISSVectorStore) -> None:
    items = _ortho_vectors()
    ids = [item[0] for item in items]
    vecs = [item[1] for item in items]
    store.upsert(ids, vecs)


# ── tests ─────────────────────────────────────────────────────────────────────


def test_faiss_upsert_and_search_returns_closest(store):
    """Query vector returns its own id at rank 1."""
    _populate(store)
    results = store.search([1.0, 0.0, 0.0, 0.0], k=1)
    assert len(results) == 1
    assert results[0][0] == "a"


def test_faiss_cosine_score_of_identical_vector(store):
    """Identical query → score ≈ 1.0."""
    _populate(store)
    results = store.search([1.0, 0.0, 0.0, 0.0], k=1)
    assert abs(results[0][1] - 1.0) < 1e-5


def test_faiss_upsert_merge_preserves_prior_entries(store):
    """Second upsert() call doesn't lose entries from the first."""
    store.upsert(["a"], [[1.0, 0.0, 0.0, 0.0]])
    store.upsert(["b"], [[0.0, 1.0, 0.0, 0.0]])

    # "a" should still be retrievable
    results = store.search([1.0, 0.0, 0.0, 0.0], k=2)
    ids = [r[0] for r in results]
    assert "a" in ids


def test_faiss_search_respects_k(store):
    """len(results) <= k."""
    _populate(store)
    results = store.search([1.0, 0.0, 0.0, 0.0], k=2)
    assert len(results) <= 2


def test_faiss_search_on_empty_store_returns_empty(store):
    """[] before any upsert()."""
    results = store.search([1.0, 0.0, 0.0, 0.0], k=5)
    assert results == []


def test_faiss_save_and_load_roundtrip(store, tmp_path):
    """save() → load() → search() returns same results."""
    _populate(store)
    index_path = str(tmp_path / "catalog.faiss")
    store.save(index_path)

    loaded = FAISSVectorStore.load(index_path)
    original_results = store.search([1.0, 0.0, 0.0, 0.0], k=1)
    loaded_results = loaded.search([1.0, 0.0, 0.0, 0.0], k=1)

    assert loaded_results[0][0] == original_results[0][0]
    assert abs(loaded_results[0][1] - original_results[0][1]) < 1e-5


def test_faiss_save_without_path_raises(store):
    """save() with no path and no index_path → ValueError."""
    _populate(store)
    with pytest.raises(ValueError, match="No path provided"):
        store.save()


def test_faiss_load_nonexistent_path_raises():
    """load("nonexistent") → FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        FAISSVectorStore.load("nonexistent_path_that_does_not_exist.faiss")
