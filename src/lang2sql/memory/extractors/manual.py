"""ManualExtractor — the V1 Extractor axis (★②).

In V1 the only way a fact is born is the explicit ``/remember`` command, so
automatic extraction from the transcript yields nothing. v1.5 swaps in an
LLM-backed extractor that mines repeated patterns — same :class:`ExtractorPort`.
"""

from __future__ import annotations

from typing import Sequence

from ...core.ports.memory import Fact
from ...core.types import Message


class ManualExtractor:
    """``ExtractorPort`` that never auto-creates facts."""

    async def extract(self, owner: str, transcript: Sequence[Message]) -> list[Fact]:
        return []
