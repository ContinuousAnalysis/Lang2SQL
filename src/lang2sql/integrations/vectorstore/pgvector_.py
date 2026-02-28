from __future__ import annotations

from ...core.exceptions import IntegrationMissingError
from ...core.ports import VectorStorePort

try:
    import psycopg2 as _psycopg2
    from pgvector.psycopg2 import register_vector as _register_vector
except ImportError:
    _psycopg2 = None  # type: ignore[assignment]
    _register_vector = None  # type: ignore[assignment]


class PGVectorStore(VectorStorePort):
    """
    PostgreSQL pgvector-backed vector store.

    True upsert semantics via ON CONFLICT DO UPDATE — idempotent,
    no duplicates across multiple from_chunks() runs.
    Table is created automatically on first upsert() call.

    Args:
        connection:  PostgreSQL connection URL.
                     e.g. "postgresql://user:pass@localhost:5432/mydb"
        table_name:  Name of the vector table. Default "lang2sql_vectors".

    Installation:
        pip install psycopg2-binary pgvector

    Quick start with Docker:
        docker run -d -e POSTGRES_PASSWORD=postgres \\
            -p 5432:5432 pgvector/pgvector:pg16
    """

    def __init__(
        self,
        *,
        connection: str,
        table_name: str = "lang2sql_vectors",
    ) -> None:
        if _psycopg2 is None or _register_vector is None:
            raise IntegrationMissingError(
                "psycopg2", hint="pip install psycopg2-binary pgvector"
            )
        self._conn = _psycopg2.connect(connection)
        _register_vector(self._conn)
        self._table = table_name
        self._ready = False  # True after first _ensure_table()

    def _ensure_table(self, dim: int) -> None:
        if self._ready:
            return
        with self._conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            cur.execute(
                f"CREATE TABLE IF NOT EXISTS {self._table} "
                f"(id TEXT PRIMARY KEY, embedding vector({dim}));"
            )
        self._conn.commit()
        self._ready = True

    # ── VectorStorePort ──────────────────────────────────────────────

    def upsert(self, ids: list[str], vectors: list[list[float]]) -> None:
        """Create table if needed, then upsert all (id, vector) pairs."""
        if not vectors:
            return
        self._ensure_table(len(vectors[0]))
        with self._conn.cursor() as cur:
            for id_, vec in zip(ids, vectors):
                cur.execute(
                    f"INSERT INTO {self._table} (id, embedding) VALUES (%s, %s) "
                    "ON CONFLICT (id) DO UPDATE SET embedding = EXCLUDED.embedding;",
                    (id_, vec),
                )
        self._conn.commit()

    def search(self, vector: list[float], k: int) -> list[tuple[str, float]]:
        """Return (chunk_id, cosine_score) for the k nearest vectors.
        Returns [] if the table has not been created yet.
        """
        if not self._ready:
            return []
        with self._conn.cursor() as cur:
            cur.execute(
                f"SELECT id, 1 - (embedding <=> %s::vector) AS score "
                f"FROM {self._table} "
                f"ORDER BY embedding <=> %s::vector LIMIT %s;",
                (vector, vector, k),
            )
            return [(row[0], float(row[1])) for row in cur.fetchall()]
