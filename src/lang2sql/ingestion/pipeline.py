"""IngestionPipeline — drives the Source × Extractor matrix (★③).

A document is fetched from a Source then handed to an Extractor; the resulting
candidates are shown for user confirmation before they land in the semantic
layer (documents stay the source of truth). The pipeline itself is axis-blind:
any Source pairs with any Extractor.
"""

from __future__ import annotations

from ..core.ports.ingestion import (
    DocExtractorPort,
    SemanticCandidate,
    SourcePort,
)


class IngestionPipeline:
    """Fetch a document from ``source`` then extract candidates with ``extractor``."""

    async def ingest(
        self,
        source: SourcePort,
        extractor: DocExtractorPort,
        ref: str,
        blob: bytes | None = None,
    ) -> list[SemanticCandidate]:
        doc = await source.fetch(ref, blob)
        return await extractor.extract(doc)
