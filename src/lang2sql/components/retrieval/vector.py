from __future__ import annotations

from typing import Optional

from ...core.base import BaseComponent
from ...core.catalog import CatalogEntry, IndexedChunk, RetrievalResult, TextDocument
from ...core.hooks import TraceHook
from ...core.ports import EmbeddingPort, VectorStorePort
from .chunker import CatalogChunker, DocumentChunkerPort


class VectorRetriever(BaseComponent):
    """
    Catalog + business document retrieval via vector similarity.

    RetrievalResult.schemas is deduplicated by source table — multiple chunks
    from the same table produce only one CatalogEntry in the result.

    Two construction patterns:

    1. One-touch factory (quick start):
        retriever = VectorRetriever.from_sources(catalog=..., embedding=...)
        retriever.add(RecursiveCharacterChunker().split(more_docs))  # incremental

    2. Explicit pipeline (full control, LangChain-style):
        chunks = (
            CatalogChunker().split(catalog) +
            RecursiveCharacterChunker().split(docs)
        )
        retriever = VectorRetriever.from_chunks(chunks, embedding=embedding, top_n=5)
        retriever.add(RecursiveCharacterChunker().split(new_docs))  # incremental

    Args:
        vectorstore:     VectorStorePort implementation.
        embedding:       EmbeddingPort implementation.
        registry:        dict[chunk_id, IndexedChunk] mapping.
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

    @classmethod
    def from_chunks(
        cls,
        chunks: list[IndexedChunk],
        *,
        embedding: EmbeddingPort,
        vectorstore: Optional[VectorStorePort] = None,
        top_n: int = 5,
        score_threshold: float = 0.0,
        name: Optional[str] = None,
        hook: Optional[TraceHook] = None,
    ) -> "VectorRetriever":
        """
        LangChain-style factory: build from pre-split chunks.

        Embeds and stores the given chunks; no splitting is performed here.
        Use chunker.split(docs) before calling this method.

        Args:
            chunks:          Pre-split list[IndexedChunk] (e.g. from CatalogChunker.split()).
            embedding:       EmbeddingPort implementation.
            vectorstore:     Defaults to InMemoryVectorStore.
            top_n:           Maximum schemas and context items to return. Default 5.
            score_threshold: Score cutoff. Default 0.0.
        """
        from ...integrations.vectorstore.inmemory_ import InMemoryVectorStore

        store = vectorstore or InMemoryVectorStore()
        registry: dict = {}
        if chunks:
            ids = [c["chunk_id"] for c in chunks]
            texts = [c["text"] for c in chunks]
            vectors = embedding.embed_texts(texts)
            store.upsert(ids, vectors)
            registry.update({c["chunk_id"]: c for c in chunks})

        return cls(
            vectorstore=store,
            embedding=embedding,
            registry=registry,
            top_n=top_n,
            score_threshold=score_threshold,
            name=name,
            hook=hook,
        )

    @classmethod
    def from_sources(
        cls,
        *,
        catalog: list[CatalogEntry],
        embedding: EmbeddingPort,
        documents: Optional[list[TextDocument]] = None,
        splitter: Optional[DocumentChunkerPort] = None,
        vectorstore: Optional[VectorStorePort] = None,
        top_n: int = 5,
        score_threshold: float = 0.0,
        name: Optional[str] = None,
        hook: Optional[TraceHook] = None,
    ) -> "VectorRetriever":
        """
        One-touch factory: chunk, embed, and index in a single call.

        Internally calls from_chunks() after splitting catalog and documents.
        For incremental addition after construction, use retriever.add(chunks).

        Args:
            catalog:          List of CatalogEntry dicts to index.
            embedding:        EmbeddingPort implementation.
            documents:        Optional list of TextDocument to index alongside catalog.
            splitter:         Chunker for documents. Defaults to RecursiveCharacterChunker.
                              Pass SemanticChunker(embedding=...) for higher quality.
            vectorstore:      Defaults to InMemoryVectorStore.
            top_n:            Maximum schemas and context items to return. Default 5.
            score_threshold:  Score cutoff. Default 0.0.
        """
        from .chunker import RecursiveCharacterChunker

        _splitter = splitter or RecursiveCharacterChunker()
        chunks = CatalogChunker().split(catalog)
        if documents:
            chunks = chunks + _splitter.split(documents)

        return cls.from_chunks(
            chunks,
            embedding=embedding,
            vectorstore=vectorstore,
            top_n=top_n,
            score_threshold=score_threshold,
            name=name,
            hook=hook,
        )

    def add(self, chunks: list[IndexedChunk]) -> None:
        """
        Add pre-split chunks to the index incrementally.

        Use chunker.split(docs) before calling this method.

        Args:
            chunks: list[IndexedChunk] from chunker.split().
        """
        if not chunks:
            return
        ids = [c["chunk_id"] for c in chunks]
        texts = [c["text"] for c in chunks]
        vectors = self._embedding.embed_texts(texts)
        self._vectorstore.upsert(ids, vectors)
        self._registry.update({c["chunk_id"]: c for c in chunks})

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
