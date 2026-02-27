from __future__ import annotations

from ...core.catalog import IndexedChunk, TextDocument
from ...core.exceptions import IntegrationMissingError
from ...core.ports import EmbeddingPort


class SemanticChunker:
    """
    Embedding-based semantic chunker. Optional — explicit opt-in only.

    Splits text into sentences, computes cosine similarity between adjacent
    sentences, and treats similarity drop-offs as chunk boundaries.
    Produces more semantically coherent chunks than RecursiveCharacterChunker.

    Note: embedding API is called during indexing (not just at query time).
    Consider the cost and latency before choosing this over RecursiveCharacterChunker.

    Limitation: sentence splitting uses punctuation and newlines. Languages without
    whitespace word boundaries (e.g. Korean) rely on sentence-ending punctuation
    (., !, ?, 。) or newlines for splits. Accuracy may vary for dense prose.

    Args:
        embedding:            EmbeddingPort implementation (can be shared with VectorRetriever).
        breakpoint_threshold: Similarity drop threshold for boundary detection. Default 0.3.
                              Lower values produce more (smaller) chunks.
        min_chunk_size:       Minimum characters per chunk; short chunks are merged
                              into the previous one. Default 100.

    Example::

        from lang2sql.integrations.embedding import OpenAIEmbedding
        from lang2sql.integrations.chunking import SemanticChunker

        embedding = OpenAIEmbedding()
        chunker = SemanticChunker(embedding=embedding)

        retriever = VectorRetriever.from_sources(..., splitter=chunker)
    """

    def __init__(
        self,
        *,
        embedding: EmbeddingPort,
        breakpoint_threshold: float = 0.3,
        min_chunk_size: int = 100,
    ) -> None:
        try:
            import numpy as _np  # noqa: F401
        except ImportError:
            raise IntegrationMissingError("numpy", hint="pip install numpy")
        self._embedding = embedding
        self._threshold = breakpoint_threshold
        self._min_size = min_chunk_size

    def split(self, docs: list[TextDocument]) -> list[IndexedChunk]:
        """LangChain-style batch split: list input → list output."""
        return [c for doc in docs for c in self.chunk(doc)]

    def chunk(self, doc: TextDocument) -> list[IndexedChunk]:
        import numpy as np

        content = doc.get("content", "")
        if not content:
            return []

        sentences = self._split_sentences(content)
        if len(sentences) <= 1:
            return self._make_chunks(doc, [content])

        embeddings = self._embedding.embed_texts(sentences)
        mat = np.array(embeddings, dtype=np.float32)
        norms = np.linalg.norm(mat, axis=1, keepdims=True)
        mat = mat / (norms + 1e-8)

        # cosine similarity between adjacent sentences — shape: (n-1,)
        sims = (mat[:-1] * mat[1:]).sum(axis=1)

        # positions where similarity drops sharply are chunk boundaries
        boundaries = [0]
        for i, sim in enumerate(sims):
            if sim < (1.0 - self._threshold):
                boundaries.append(i + 1)
        boundaries.append(len(sentences))

        raw_chunks: list[str] = []
        for start, end in zip(boundaries, boundaries[1:]):
            chunk_text = " ".join(sentences[start:end])
            if len(chunk_text) < self._min_size and raw_chunks:
                raw_chunks[-1] += (
                    " " + chunk_text
                )  # merge short trailing chunk into previous
            else:
                raw_chunks.append(chunk_text)

        return self._make_chunks(doc, raw_chunks)

    def _split_sentences(self, text: str) -> list[str]:
        """Split on sentence-ending punctuation or newlines. No external tokenizer needed."""
        import re

        parts = re.split(r"(?<=[.!?。])\s+|\n+", text.strip())
        return [p.strip() for p in parts if p.strip()]

    def _make_chunks(self, doc: TextDocument, texts: list[str]) -> list[IndexedChunk]:
        title = doc.get("title", "")
        doc_id = doc.get("id", "")
        return [
            IndexedChunk(
                chunk_id=f"{doc_id}__{i}",
                text=f"{title}: {text}" if title else text,
                source_type="document",
                source_id=doc_id,
                chunk_index=i,
                metadata={
                    "id": doc_id,
                    "title": title,
                    "source": doc.get("source", ""),
                },
            )
            for i, text in enumerate(texts)
        ]
