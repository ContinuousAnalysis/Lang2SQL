from __future__ import annotations

from typing import Optional

from ...core.base import BaseComponent
from ...core.catalog import CatalogEntry, RetrievalResult, TextDocument
from ...core.hooks import TraceHook
from ...core.ports import EmbeddingPort
from .chunker import DocumentChunkerPort
from .keyword import KeywordRetriever
from .vector import VectorRetriever


class HybridRetriever(BaseComponent):
    """
    BM25 + vector hybrid retriever. Merges results with Reciprocal Rank Fusion (RRF).

    RRF algorithm::

        RRF_score(table) = Σ 1/(k + rank_i)   for each ranker i
        k = 60  (default, recommended by the RRF paper)

    Over-fetches ``top_n * 2`` candidates from each retriever, merges via RRF,
    and returns the final ``top_n``.
    Context is taken from VectorRetriever only (BM25 has no document context).

    Args:
        catalog:          List of CatalogEntry dicts.
        embedding:        EmbeddingPort implementation.
        documents:        Optional list of business documents to index.
        splitter:         Chunking strategy for documents (default: RecursiveCharacterChunker).
        top_n:            Maximum number of schemas to return. Default 5.
        rrf_k:            RRF smoothing constant. Default 60.
        score_threshold:  Minimum vector similarity score. Default 0.0.
        name:             Component name for tracing.
        hook:             TraceHook for observability.

    Usage::

        retriever = HybridRetriever(
            catalog=[{"name": "orders", "description": "...", "columns": {...}}],
            embedding=OpenAIEmbedding(model="text-embedding-3-small"),
        )
        result = retriever("How many orders last month?")  # RetrievalResult
    """

    def __init__(
        self,
        *,
        catalog: list[CatalogEntry],
        embedding: EmbeddingPort,
        documents: Optional[list[TextDocument]] = None,
        splitter: Optional[DocumentChunkerPort] = None,
        top_n: int = 5,
        rrf_k: int = 60,
        score_threshold: float = 0.0,
        name: Optional[str] = None,
        hook: Optional[TraceHook] = None,
    ) -> None:
        super().__init__(name=name or "HybridRetriever", hook=hook)
        fetch = top_n * 2
        self._keyword = KeywordRetriever(catalog=catalog, top_n=fetch)
        self._vector = VectorRetriever.from_sources(
            catalog=catalog,
            embedding=embedding,
            documents=documents,
            splitter=splitter,
            top_n=fetch,
            score_threshold=score_threshold,
        )
        self._top_n = top_n
        self._rrf_k = rrf_k

    def _run(self, query: str) -> RetrievalResult:
        """
        Args:
            query: Natural language search query.

        Returns:
            RetrievalResult:
                .schemas — top_n schemas after RRF merge
                .context — business document context from VectorRetriever
        """
        keyword_schemas = self._keyword(query)          # list[CatalogEntry]
        vector_result   = self._vector(query)           # RetrievalResult

        merged = self._rrf_merge(keyword_schemas, vector_result.schemas)
        return RetrievalResult(schemas=merged, context=vector_result.context)

    def _rrf_merge(
        self,
        keyword_schemas: list[CatalogEntry],
        vector_schemas: list[CatalogEntry],
    ) -> list[CatalogEntry]:
        """Merge results from both retrievers via RRF and return top_n entries."""
        k = self._rrf_k
        scores: dict[str, float] = {}
        entries: dict[str, CatalogEntry] = {}

        for rank, entry in enumerate(keyword_schemas, start=1):
            name = entry["name"]
            scores[name] = scores.get(name, 0.0) + 1.0 / (k + rank)
            entries[name] = entry

        for rank, entry in enumerate(vector_schemas, start=1):
            name = entry["name"]
            scores[name] = scores.get(name, 0.0) + 1.0 / (k + rank)
            if name not in entries:
                entries[name] = entry

        sorted_names = sorted(scores, key=lambda n: scores[n], reverse=True)
        return [entries[n] for n in sorted_names[: self._top_n]]
