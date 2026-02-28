"""
PGVectorStore integration tests.

Requires a live PostgreSQL instance with pgvector installed.
Skipped when TEST_POSTGRES_URL env variable is not set.

Example:
    TEST_POSTGRES_URL="postgresql://postgres:postgres@localhost:5432/test" \\
        pytest tests/test_integrations_pgvector_vectorstore.py -v
"""

import os
import pytest
from uuid import uuid4

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_POSTGRES_URL"),
    reason="TEST_POSTGRES_URL not set — skipping pgvector integration tests",
)

from lang2sql.integrations.vectorstore.pgvector_ import PGVectorStore

# ── helpers ──────────────────────────────────────────────────────────────────


def _unique_table() -> str:
    return f"test_{uuid4().hex[:8]}"


def _make_store(table_name: str) -> PGVectorStore:
    url = os.environ["TEST_POSTGRES_URL"]
    return PGVectorStore(connection=url, table_name=table_name)


def _drop_table(store: PGVectorStore, table_name: str) -> None:
    with store._conn.cursor() as cur:
        cur.execute(f"DROP TABLE IF EXISTS {table_name};")
    store._conn.commit()


# ── tests ─────────────────────────────────────────────────────────────────────


def test_pgvector_upsert_and_search():
    """Query vector returns its own id."""
    table = _unique_table()
    store = _make_store(table)
    try:
        store.upsert(["a"], [[1.0, 0.0, 0.0, 0.0]])
        results = store.search([1.0, 0.0, 0.0, 0.0], k=1)
        assert len(results) == 1
        assert results[0][0] == "a"
    finally:
        _drop_table(store, table)
        store._conn.close()


def test_pgvector_upsert_is_idempotent():
    """Same id upserted twice → exactly one row in DB."""
    table = _unique_table()
    store = _make_store(table)
    try:
        store.upsert(["a"], [[1.0, 0.0, 0.0, 0.0]])
        store.upsert(["a"], [[0.5, 0.5, 0.0, 0.0]])  # overwrite same id

        with store._conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {table} WHERE id = 'a';")
            count = cur.fetchone()[0]
        assert count == 1
    finally:
        _drop_table(store, table)
        store._conn.close()


def test_pgvector_search_score_in_range():
    """Score ∈ [-1, 1]."""
    table = _unique_table()
    store = _make_store(table)
    try:
        store.upsert(
            ["a", "b", "c"],
            [
                [1.0, 0.0, 0.0, 0.0],
                [0.0, 1.0, 0.0, 0.0],
                [0.0, 0.0, 1.0, 0.0],
            ],
        )
        results = store.search([1.0, 0.0, 0.0, 0.0], k=3)
        for _, score in results:
            assert -1.0 <= score <= 1.0 + 1e-6
    finally:
        _drop_table(store, table)
        store._conn.close()


def test_pgvector_search_respects_k():
    """len(results) <= k."""
    table = _unique_table()
    store = _make_store(table)
    try:
        store.upsert(
            ["a", "b", "c", "d"],
            [
                [1.0, 0.0, 0.0, 0.0],
                [0.0, 1.0, 0.0, 0.0],
                [0.0, 0.0, 1.0, 0.0],
                [0.0, 0.0, 0.0, 1.0],
            ],
        )
        results = store.search([1.0, 0.0, 0.0, 0.0], k=2)
        assert len(results) <= 2
    finally:
        _drop_table(store, table)
        store._conn.close()


def test_pgvector_table_created_automatically():
    """Table exists in information_schema after first upsert()."""
    table = _unique_table()
    store = _make_store(table)
    try:
        store.upsert(["x"], [[1.0, 0.0]])
        with store._conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_name = %s;",
                (table,),
            )
            count = cur.fetchone()[0]
        assert count == 1
    finally:
        _drop_table(store, table)
        store._conn.close()


def test_pgvector_search_empty_store_returns_empty():
    """[] before any upsert()."""
    table = _unique_table()
    store = _make_store(table)
    try:
        results = store.search([1.0, 0.0, 0.0, 0.0], k=5)
        assert results == []
    finally:
        store._conn.close()
