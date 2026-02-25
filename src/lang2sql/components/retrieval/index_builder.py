from __future__ import annotations

from typing import Optional

from ...core.base import BaseComponent
from ...core.catalog import CatalogEntry, IndexedChunk, TextDocument
from ...core.hooks import TraceHook
from ...core.ports import EmbeddingPort, VectorStorePort
from .chunker import CatalogChunker, DocumentChunkerPort, RecursiveCharacterChunker


class IndexBuilder(BaseComponent):
    """
    Chunks and indexes CatalogEntry or TextDocument lists into a vector store.

    IndexBuilder and VectorRetriever share the same registry:
        registry: dict[str, IndexedChunk] = {}
        builder   = IndexBuilder(..., registry=registry)
        retriever = VectorRetriever(..., registry=registry)

    Type detection in _run():
        - Items with a "name" key (and no "content") → CatalogEntry → CatalogChunker
        - Items with a "content" key                 → TextDocument  → document_chunker

    The document_chunker defaults to RecursiveCharacterChunker.
    Replace it with SemanticChunker or any DocumentChunkerPort implementation as needed.

    Args:
        embedding:        EmbeddingPort implementation.
        vectorstore:      VectorStorePort implementation.
        registry:         Shared chunk metadata store (also passed to VectorRetriever).
        catalog_chunker:  Defaults to CatalogChunker(max_columns_per_chunk=20).
        document_chunker: Defaults to RecursiveCharacterChunker().
        name:             Component name for tracing.
        hook:             TraceHook for observability.
    """

    def __init__(
        self,
        *,
        embedding: EmbeddingPort,
        vectorstore: VectorStorePort,
        registry: dict,
        catalog_chunker: Optional[CatalogChunker] = None,
        document_chunker: Optional[DocumentChunkerPort] = None,
        name: Optional[str] = None,
        hook: Optional[TraceHook] = None,
    ) -> None:
        super().__init__(name=name or "IndexBuilder", hook=hook)
        self._embedding = embedding
        self._vectorstore = vectorstore
        self._registry = registry
        self._catalog_chunker = catalog_chunker or CatalogChunker()
        self._document_chunker = document_chunker or RecursiveCharacterChunker()

    def _run(self, items: list) -> None:
        """
        Args:
            items: list[CatalogEntry] or list[TextDocument].
                   Mixed lists are not supported — type is determined from the first item.
        Returns:
            None (modifies vectorstore and registry in-place).
        """
        if not items:
            return

        first = items[0]
        # CatalogEntry always has "name"; TextDocument always has "content".
        # Checking "name" absence is more robust than checking "content" presence
        # because a CatalogEntry could carry arbitrary extra keys including "content".
        is_document = "content" in first and "name" not in first

        # Mixed lists are not supported — raise early rather than silently misclassifying.
        for item in items[1:]:
            item_is_document = "content" in item and "name" not in item
            if item_is_document != is_document:
                raise ValueError(
                    "Mixed lists are not supported. "
                    "Pass either list[CatalogEntry] (items with 'name') "
                    "or list[TextDocument] (items with 'content'), not both."
                )

        if is_document:
            chunks: list[IndexedChunk] = [
                c for doc in items for c in self._document_chunker.chunk(doc)
            ]
        else:
            chunks = [c for entry in items for c in self._catalog_chunker.chunk(entry)]

        if not chunks:
            return

        ids = [c["chunk_id"] for c in chunks]
        texts = [c["text"] for c in chunks]
        vectors = self._embedding.embed_texts(texts)

        self._vectorstore.upsert(ids, vectors)
        self._registry.update({c["chunk_id"]: c for c in chunks})
