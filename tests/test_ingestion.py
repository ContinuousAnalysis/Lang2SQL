"""Ingestion V1 — LLM extraction and pipeline wiring (★③)."""

from __future__ import annotations

import asyncio
import os
import tempfile
from typing import Sequence

from lang2sql.core.ports.ingestion import CandidateKind, Document
from lang2sql.core.types import Completion, Message, ToolSpec
from lang2sql.ingestion import FileSource, IngestionPipeline, LLMExtractor


class _ScriptedLLM:
    """Inline fake LLMPort returning a fixed completion content."""

    def __init__(self, content: str) -> None:
        self._content = content

    async def complete(
        self,
        messages: Sequence[Message],
        tools: Sequence[ToolSpec] = (),
    ) -> Completion:
        return Completion(content=self._content, finish_reason="stop")


_JSON_ARRAY = """
[
  {"kind": "metric", "name": "total_revenue",
   "definition": "SUM(orders.amount)", "applies_to": "orders"},
  {"kind": "rule", "name": "exclude_cancelled",
   "definition": "status != 'cancelled'", "applies_to": "total_revenue"}
]
"""

_FENCED = "```json\n" + _JSON_ARRAY.strip() + "\n```"


def test_llm_extractor_maps_json_array_to_candidates() -> None:
    extractor = LLMExtractor(_ScriptedLLM(_JSON_ARRAY))

    async def run() -> None:
        doc = Document(name="defs.md", text="...", source_id="doc-1")
        cands = await extractor.extract(doc)
        assert [c.name for c in cands] == ["total_revenue", "exclude_cancelled"]
        assert cands[0].kind == CandidateKind.METRIC
        assert cands[1].kind == CandidateKind.RULE
        assert all(c.source_id == "doc-1" for c in cands)

    asyncio.run(run())


def test_llm_extractor_strips_json_fences() -> None:
    extractor = LLMExtractor(_ScriptedLLM(_FENCED))

    async def run() -> None:
        cands = await extractor.extract(Document(name="d", text="t", source_id="s"))
        assert len(cands) == 2

    asyncio.run(run())


def test_llm_extractor_malformed_content_returns_empty() -> None:
    async def run() -> None:
        for content in ["not json at all", "", "{not: valid}", "42", "{}"]:
            extractor = LLMExtractor(_ScriptedLLM(content))
            assert await extractor.extract(Document(name="d", text="t")) == []

    asyncio.run(run())


def test_llm_extractor_skips_rows_with_bad_kind_or_missing_fields() -> None:
    content = """
    [
      {"kind": "metric", "name": "ok", "definition": "x"},
      {"kind": "bogus", "name": "bad_kind", "definition": "y"},
      {"kind": "metric", "name": "", "definition": "z"},
      {"kind": "metric", "name": "no_def"},
      "not a dict"
    ]
    """
    extractor = LLMExtractor(_ScriptedLLM(content))

    async def run() -> None:
        cands = await extractor.extract(Document(name="d", text="t"))
        assert [c.name for c in cands] == ["ok"]

    asyncio.run(run())


def test_file_source_decodes_blob() -> None:
    source = FileSource()

    async def run() -> None:
        doc = await source.fetch("path/to/defs.md", blob=b"hello blob")
        assert doc.name == "defs.md"
        assert doc.text == "hello blob"
        assert doc.source_id == "path/to/defs.md"

    asyncio.run(run())


def test_file_source_reads_from_disk() -> None:
    source = FileSource()

    async def run() -> None:
        fd, path = tempfile.mkstemp(suffix=".txt")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write("on disk")
            doc = await source.fetch(path)
            assert doc.text == "on disk"
            assert doc.name == os.path.basename(path)
        finally:
            os.remove(path)

    asyncio.run(run())


def test_pipeline_fetches_then_extracts() -> None:
    pipeline = IngestionPipeline()
    source = FileSource()
    extractor = LLMExtractor(_ScriptedLLM(_JSON_ARRAY))

    async def run() -> None:
        cands = await pipeline.ingest(
            source, extractor, ref="defs.md", blob=b"document body"
        )
        assert [c.name for c in cands] == ["total_revenue", "exclude_cancelled"]
        assert all(c.source_id == "defs.md" for c in cands)

    asyncio.run(run())
