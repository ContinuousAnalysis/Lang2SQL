"""LLMExtractor — the V1 Extractor axis (★③).

Asks an LLM to read a document and propose metric/dimension/rule definitions as
a JSON array. Parsing is deliberately robust: ```json fences are stripped and
any malformed response degrades to an empty candidate list rather than raising.
v1.5 adds a DDL parser implementing the same :class:`DocExtractorPort`.
"""

from __future__ import annotations

import json

from ...core.ports.ingestion import (
    CandidateKind,
    Document,
    SemanticCandidate,
)
from ...core.ports.llm import LLMPort
from ...core.types import Message, Role

_INSTRUCTIONS = (
    "From this document, extract metric/dimension/rule definitions as a JSON "
    "array of {kind,name,definition,applies_to}. ``kind`` must be one of "
    '"metric", "dimension", "rule". Respond with only the JSON array.'
)


class LLMExtractor:
    """``DocExtractorPort`` that mines candidates with an LLM."""

    def __init__(self, llm: LLMPort) -> None:
        self._llm = llm

    async def extract(self, doc: Document) -> list[SemanticCandidate]:
        prompt = f"{_INSTRUCTIONS}\n\nDocument: {doc.name}\n\n{doc.text}"
        completion = await self._llm.complete([Message(role=Role.USER, content=prompt)])
        rows = _parse(completion.content)
        candidates: list[SemanticCandidate] = []
        for row in rows:
            candidate = _to_candidate(row, doc.source_id)
            if candidate is not None:
                candidates.append(candidate)
        return candidates


def _parse(content: str) -> list:
    """Parse a JSON array from raw model output; [] on any failure."""
    text = _strip_fences(content)
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        return []
    return data if isinstance(data, list) else []


def _strip_fences(content: str) -> str:
    """Drop a surrounding ```json ... ``` fence if present."""
    text = (content or "").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # Drop opening fence (```json or ```) and a trailing fence if present.
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def _to_candidate(row: object, source_id: str) -> SemanticCandidate | None:
    """Map one parsed dict to a SemanticCandidate; skip if unusable."""
    if not isinstance(row, dict):
        return None
    try:
        kind = CandidateKind(str(row.get("kind", "")).lower())
    except ValueError:
        return None
    name = row.get("name")
    definition = row.get("definition")
    if not name or not definition:
        return None
    return SemanticCandidate(
        kind=kind,
        name=str(name),
        definition=str(definition),
        applies_to=str(row.get("applies_to", "")),
        source_id=source_id,
    )
