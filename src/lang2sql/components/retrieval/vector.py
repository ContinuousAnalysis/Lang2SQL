from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from ...core.base import BaseComponent
from ...core.catalog import CatalogEntry, IndexedChunk, RetrievalResult, TextDocument
from ...core.hooks import TraceHook
from ...core.ports import EmbeddingPort, VectorStorePort
from .chunker import CatalogChunker, DocumentChunkerPort

if TYPE_CHECKING:
    from .index_builder import IndexBuilder


class VectorRetriever(BaseComponent):
    """
    Catalog + business document retrieval via vector similarity.

    Must share the same registry as the IndexBuilder used to build the index.
    RetrievalResult.schemas is deduplicated by source table — multiple chunks
    from the same table produce only one CatalogEntry in the result.

    Two construction patterns:

    1. Manual (full control, incremental indexing):
        registry: dict = {}
        builder   = IndexBuilder(embedding=..., vectorstore=..., registry=registry)
        retriever = VectorRetriever(vectorstore=..., embedding=..., registry=registry)
        builder.run(catalog)
        builder.run(docs)
        builder.run(more_docs)  # incremental — add anytime

    2. Convenience factory (quick start, build-once):
        retriever = VectorRetriever.from_sources(catalog=..., embedding=...)
        retriever.add(more_docs)  # incremental add after construction

    Args:
        vectorstore:     VectorStorePort implementation.
        embedding:       EmbeddingPort implementation.
        registry:        Shared dict[chunk_id, IndexedChunk] from IndexBuilder.
        top_n:           Maximum schemas and context items to return. Default 5.
        score_threshold: Chunks with score <= this value are excluded. Default 0.0.
        name:            Component name for tracing.
        hook:            TraceHook for observability.
    """

    def __init__(
        self,
        *,
        vectorstore: VectorStorePort,
        embedding: EmbeddingPort,
        registry: dict,
        top_n: int = 5,
        score_threshold: float = 0.0,
        name: Optional[str] = None,
        hook: Optional[TraceHook] = None,
    ) -> None:
        super().__init__(name=name or "VectorRetriever", hook=hook)
        self._vectorstore = vectorstore
        self._embedding = embedding
        self._registry = registry
        self._top_n = top_n
        self._score_threshold = score_threshold
        self._index_builder: Optional[IndexBuilder] = None  # set only by from_sources()

    @classmethod
    def from_sources(
        cls,
        *,
        catalog: list[CatalogEntry],
        embedding: EmbeddingPort,
        documents: Optional[list[TextDocument]] = None,
        document_chunker: Optional[DocumentChunkerPort] = None,
        vectorstore: Optional[VectorStorePort] = None,
        top_n: int = 5,
        score_threshold: float = 0.0,
        name: Optional[str] = None,
        hook: Optional[TraceHook] = None,
    ) -> "VectorRetriever":
        """
        Convenience factory: build index and return a ready-to-use retriever in one call.

        Internally creates InMemoryVectorStore, IndexBuilder, and shared registry,
        then runs indexing for the given catalog and optional documents.

        For incremental document addition after construction, use retriever.add().
        For full control over the indexing pipeline (custom vectorstore, load saved index,
        etc.), use IndexBuilder and VectorRetriever directly instead.

        Args:
            catalog:          List of CatalogEntry dicts to index.
            embedding:        EmbeddingPort implementation.
            documents:        Optional list of TextDocument to index alongside catalog.
            document_chunker: Chunker for documents. Defaults to RecursiveCharacterChunker.
                              Pass SemanticChunker(embedding=...) for higher quality.
            vectorstore:      Defaults to InMemoryVectorStore.
            top_n:            Maximum schemas and context items to return. Default 5.
            score_threshold:  Score cutoff. Default 0.0.
        """
        from ...integrations.vectorstore.inmemory_ import InMemoryVectorStore
        from .index_builder import IndexBuilder

        store = vectorstore or InMemoryVectorStore()
        registry: dict = {}

        builder = IndexBuilder(
            embedding=embedding,
            vectorstore=store,
            registry=registry,
            document_chunker=document_chunker,
        )
        builder.run(catalog)
        if documents:
            builder.run(documents)

        retriever = cls(
            vectorstore=store,
            embedding=embedding,
            registry=registry,
            top_n=top_n,
            score_threshold=score_threshold,
            name=name,
            hook=hook,
        )
        retriever._index_builder = builder
        return retriever

    def add(self, items: list) -> None:
        """
        Add more catalog entries or documents to the index incrementally.

        Only available on retrievers created via from_sources().
        For manually constructed retrievers, call IndexBuilder.run() directly.

        Args:
            items: list[CatalogEntry] or list[TextDocument].

        Raises:
            RuntimeError: if called on a retriever not created via from_sources().
        """
        if self._index_builder is None:
            raise RuntimeError(
                "add() is only available on retrievers created via VectorRetriever.from_sources(). "
                "For manually constructed retrievers, call IndexBuilder.run() directly."
            )
        self._index_builder.run(items)

    def _run(self, query: str) -> RetrievalResult:
        """
        Args:
            query: Natural language search query.

        Returns:
            RetrievalResult:
                .schemas — relevant CatalogEntry list (deduplicated, at most top_n)
                .context — relevant business document chunk texts (at most top_n)
        """
        if not self._registry:
            return RetrievalResult(schemas=[], context=[])

        query_vector = self._embedding.embed_query(query)
        # over-fetch by 3x so deduplication still yields top_n catalog entries
        raw = self._vectorstore.search(query_vector, k=self._top_n * 3)

        seen_tables: dict[str, CatalogEntry] = {}  # source_id → CatalogEntry (dedup)
        context: list[str] = []

        for chunk_id, score in raw:
            if score <= self._score_threshold:
                continue
            chunk = self._registry.get(chunk_id)
            if chunk is None:
                continue

            if chunk["source_type"] == "catalog":
                src = chunk["source_id"]
                if src not in seen_tables:
                    seen_tables[src] = chunk["metadata"]  # full CatalogEntry
            elif chunk["source_type"] == "document":
                context.append(chunk["text"])

        return RetrievalResult(
            schemas=list(seen_tables.values())[: self._top_n],
            context=context[: self._top_n],
        )
