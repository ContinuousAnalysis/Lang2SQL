from __future__ import annotations

from typing import Protocol, runtime_checkable

from ...core.catalog import CatalogEntry, IndexedChunk, TextDocument


@runtime_checkable
class DocumentChunkerPort(Protocol):
    """
    Interface for TextDocument → list[IndexedChunk] conversion.

    Default implementation: RecursiveCharacterChunker
    Advanced implementation: SemanticChunker (integrations/chunking/semantic_.py)
    Custom implementation: any class satisfying this Protocol can be injected into IndexBuilder.

    Example (wrapping LangChain)::

        class LangChainChunkerAdapter:
            def __init__(self, lc_splitter):
                self._splitter = lc_splitter

            def chunk(self, doc: TextDocument) -> list[IndexedChunk]:
                texts = self._splitter.split_text(doc["content"])
                return [
                    IndexedChunk(
                        chunk_id=f"{doc['id']}__{i}", text=t,
                        source_type="document", source_id=doc["id"],
                        chunk_index=i, metadata={"title": doc.get("title", "")},
                    )
                    for i, t in enumerate(texts)
                ]

        builder = IndexBuilder(..., document_chunker=LangChainChunkerAdapter(...))
    """

    def chunk(self, doc: TextDocument) -> list[IndexedChunk]: ...


class CatalogChunker:
    """
    Converts a CatalogEntry into a list of IndexedChunks.

    Solves the problem where a table with 100+ columns loses column-level
    semantics when represented as a single vector.
    Chunk 0 is a table header summary; subsequent chunks are column groups.
    Each chunk's metadata preserves the full CatalogEntry so VectorRetriever
    can reconstruct it on retrieval.

    Args:
        max_columns_per_chunk: Maximum columns per column-group chunk. Default 20.
    """

    def __init__(self, max_columns_per_chunk: int = 20) -> None:
        self._max_cols = max_columns_per_chunk

    def chunk(self, entry: CatalogEntry) -> list[IndexedChunk]:
        name = entry.get("name", "")
        description = entry.get("description", "")
        columns = entry.get("columns", {})
        chunks: list[IndexedChunk] = []

        # Chunk 0: table header
        chunks.append(
            IndexedChunk(
                chunk_id=f"{name}__0",
                text=f"{name}: {description}".strip(),
                source_type="catalog",
                source_id=name,
                chunk_index=0,
                metadata=dict(entry),  # preserve full CatalogEntry for reconstruction
            )
        )

        # Chunk 1+: column groups
        col_items = list(columns.items())
        for i, start in enumerate(range(0, len(col_items), self._max_cols)):
            group = col_items[start : start + self._max_cols]
            col_text = " ".join(f"{k} {v}" for k, v in group)
            chunks.append(
                IndexedChunk(
                    chunk_id=f"{name}__col_{i + 1}",
                    text=f"{name} columns: {col_text}",
                    source_type="catalog",
                    source_id=name,
                    chunk_index=i + 1,
                    metadata=dict(entry),  # preserve full CatalogEntry in every column chunk
                )
            )

        return chunks


class RecursiveCharacterChunker:
    """
    Hierarchical separator-based document chunker. No external dependencies.

    Separator priority: ["\\n\\n", "\\n", ". ", " ", ""]
    — tries paragraph → line → sentence → word boundaries in order.
    Character-count-based so it works for both Korean and English
    (unlike str.split() which assumes whitespace-delimited words).

    For higher chunking quality, use SemanticChunker (integrations/chunking/semantic_.py).

    Args:
        chunk_size:    Maximum characters per chunk. Default 1000.
        chunk_overlap: Overlap characters between consecutive chunks. Default 100.
        separators:    Separator priority list. None uses the default list above.
    """

    _DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 100,
        separators: list[str] | None = None,
    ) -> None:
        if chunk_overlap >= chunk_size:
            raise ValueError(
                f"chunk_overlap ({chunk_overlap}) must be less than chunk_size ({chunk_size})"
            )
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._separators = separators or self._DEFAULT_SEPARATORS

    def chunk(self, doc: TextDocument) -> list[IndexedChunk]:
        content = doc.get("content", "")
        if not content:
            return []

        raw_chunks = self._split(content, self._separators)
        title = doc.get("title", "")
        doc_id = doc.get("id", "")

        return [
            IndexedChunk(
                chunk_id=f"{doc_id}__{i}",
                text=f"{title}: {text}" if title else text,
                source_type="document",
                source_id=doc_id,
                chunk_index=i,
                metadata={"id": doc_id, "title": title, "source": doc.get("source", "")},
            )
            for i, text in enumerate(raw_chunks)
        ]

    def _split(self, text: str, separators: list[str]) -> list[str]:
        """Recursively try separators until all chunks fit within chunk_size."""
        chunks: list[str] = []
        separator = separators[-1]  # fallback: character-level split

        for sep in separators:
            if sep and sep in text:
                separator = sep
                break

        parts = text.split(separator) if separator else list(text)
        current = ""

        for part in parts:
            candidate = (current + separator + part).lstrip(separator) if current else part
            if len(candidate) <= self._chunk_size:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                # part itself exceeds chunk_size → recurse with finer separators
                if len(part) > self._chunk_size and len(separators) > 1:
                    chunks.extend(self._split(part, separators[1:]))
                    current = ""
                else:
                    current = part

        if current:
            chunks.append(current)

        if self._chunk_overlap > 0 and len(chunks) > 1:
            chunks = self._apply_overlap(chunks)

        return chunks

    def _apply_overlap(self, chunks: list[str]) -> list[str]:
        overlapped = [chunks[0]]
        for i in range(1, len(chunks)):
            prev_tail = chunks[i - 1][-self._chunk_overlap:]
            overlapped.append(prev_tail + chunks[i])
        return overlapped
