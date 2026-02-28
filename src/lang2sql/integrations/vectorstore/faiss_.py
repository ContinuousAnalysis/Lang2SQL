from __future__ import annotations

import json
import pathlib

from ...core.exceptions import IntegrationMissingError
from ...core.ports import VectorStorePort

try:
    import faiss as _faiss
    import numpy as _np
except ImportError:
    _faiss = None  # type: ignore[assignment]
    _np = None  # type: ignore[assignment]


class FAISSVectorStore(VectorStorePort):
    """
    FAISS-backed vector store with optional file persistence.

    Uses IndexFlatIP + L2 normalization for exact cosine similarity.
    Index is lazy-initialized on the first upsert() call.

    Known limitation (append-only):
        Upserting the same chunk_id twice creates duplicate FAISS entries.
        To rebuild a clean index, create a new FAISSVectorStore instance
        and run from_chunks() again from scratch.

    Args:
        index_path: Optional path for save() / load(). Used as default
                    path when save() is called without an explicit argument.

    Installation:
        pip install faiss-cpu        # CPU-only
        pip install faiss-gpu        # GPU variant
    """

    def __init__(self, index_path: str | None = None) -> None:
        if _faiss is None or _np is None:
            raise IntegrationMissingError("faiss", hint="pip install faiss-cpu")
        self._index_path = index_path
        self._index: object | None = None  # faiss.IndexFlatIP, None until first upsert
        self._ids: list[str] = []

    # ── VectorStorePort ──────────────────────────────────────────────

    def upsert(self, ids: list[str], vectors: list[list[float]]) -> None:
        """L2-normalize and add vectors. Lazy-creates index on first call."""
        arr = _np.array(vectors, dtype=_np.float32)
        _faiss.normalize_L2(arr)  # in-place cosine trick
        if self._index is None:
            self._index = _faiss.IndexFlatIP(arr.shape[1])
        self._index.add(arr)
        self._ids.extend(ids)

    def search(self, vector: list[float], k: int) -> list[tuple[str, float]]:
        """Return (chunk_id, cosine_score) for the k nearest vectors."""
        if self._index is None or self._index.ntotal == 0:
            return []
        q = _np.array([vector], dtype=_np.float32)
        _faiss.normalize_L2(q)
        k = min(k, self._index.ntotal)
        scores, positions = self._index.search(q, k)
        return [
            (self._ids[int(pos)], float(scores[0][j]))
            for j, pos in enumerate(positions[0])
            if pos >= 0
        ]

    # ── Persistence ──────────────────────────────────────────────────

    def save(self, path: str | None = None) -> None:
        """
        Write index to {path} and id list to {path}.meta.
        Falls back to self._index_path when path is None.
        Raises ValueError if no path is available.
        Raises RuntimeError if called before any upsert().
        """
        path = path or self._index_path
        if path is None:
            raise ValueError(
                "No path provided and index_path was not set at construction."
            )
        if self._index is None:
            raise RuntimeError("Cannot save before any upsert() call.")
        pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
        _faiss.write_index(self._index, path)
        pathlib.Path(path + ".meta").write_text(json.dumps(self._ids), encoding="utf-8")

    @classmethod
    def load(cls, path: str) -> "FAISSVectorStore":
        """
        Load index from {path} and id list from {path}.meta.
        Raises FileNotFoundError if either file is missing.
        """
        if _faiss is None or _np is None:
            raise IntegrationMissingError("faiss", hint="pip install faiss-cpu")
        meta_path = pathlib.Path(path + ".meta")
        if not pathlib.Path(path).exists() or not meta_path.exists():
            raise FileNotFoundError(f"Index files not found: {path}, {path}.meta")
        store = cls(index_path=path)
        store._index = _faiss.read_index(path)
        store._ids = json.loads(meta_path.read_text(encoding="utf-8"))
        return store
