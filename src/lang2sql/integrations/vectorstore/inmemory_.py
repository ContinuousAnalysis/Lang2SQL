from __future__ import annotations

from ...core.exceptions import IntegrationMissingError

try:
    import numpy as _np
except ImportError:
    _np = None  # type: ignore[assignment]


class InMemoryVectorStore:
    """
    Brute-force cosine similarity vector store backed by numpy.

    upsert merges new entries into the existing store (true upsert — no data loss
    across multiple calls). Rebuilds the matrix from a dict on each search call,
    so duplicate chunk_ids are overwritten rather than duplicated.

    Handles tens of thousands of vectors without issue. No faiss dependency required.

    For larger scale or persistence, use FAISSVectorStore / PGVectorStore (next PR).
    For advanced vector stores (Chroma, Qdrant, etc.), implement VectorStorePort directly.
    """

    def __init__(self) -> None:
        if _np is None:
            raise IntegrationMissingError("numpy", hint="pip install numpy")
        self._store: dict[str, list[float]] = {}  # chunk_id → vector

    def upsert(self, ids: list[str], vectors: list[list[float]]) -> None:
        # Merge into existing store — preserves vectors from previous upsert calls.
        # Duplicate ids overwrite the existing entry (true upsert semantics).
        for id_, vec in zip(ids, vectors):
            self._store[id_] = vec

    def search(self, vector: list[float], k: int) -> list[tuple[str, float]]:
        if not self._store:
            return []

        ids = list(self._store.keys())
        matrix = _np.array(list(self._store.values()), dtype=_np.float32)
        q = _np.array(vector, dtype=_np.float32)

        norms = _np.linalg.norm(matrix, axis=1)
        q_norm = _np.linalg.norm(q)
        sims = matrix @ q / (norms * q_norm + 1e-8)

        k = min(k, len(ids))
        top_k = _np.argsort(sims)[::-1][:k]
        return [(ids[int(i)], float(sims[i])) for i in top_k]
