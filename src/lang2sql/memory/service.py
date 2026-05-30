"""MemoryService — binds the three memory axes into one usable surface (★②).

Store, Recall and Extractor are injected, so a version bump is an adapter swap
at the wiring site rather than a change here. The service offers the three
operations the rest of the system needs: write a fact (``remember``), fetch the
relevant ones for a turn (``recall``), and render them for the prompt
(``render``).
"""

from __future__ import annotations

import time
import uuid

from ..core.ports.memory import ExtractorPort, Fact, RecallPort, StorePort


class MemoryService:
    """Coordinates the Store / Recall / Extractor axes."""

    def __init__(
        self,
        store: StorePort,
        recall: RecallPort,
        extractor: ExtractorPort,
    ) -> None:
        self._store = store
        self._recall = recall
        self._extractor = extractor

    async def remember(self, owner: str, text: str) -> Fact:
        """Create and persist a manual fact, returning it."""
        fact = Fact(
            id=str(uuid.uuid4()),
            owner=owner,
            text=text,
            source="manual",
            ts=time.time(),
        )
        await self._store.add(fact)
        return fact

    async def recall(self, owner: str, query: str) -> list[Fact]:
        """Surface the facts the recall strategy deems relevant to ``query``."""
        return await self._recall.recall(owner, query, self._store)

    def render(self, facts: list[Fact]) -> str:
        """Render facts as a markdown block for the system prompt ("" if none)."""
        if not facts:
            return ""
        lines = ["## Remembered facts"]
        lines.extend(f"- {fact.text}" for fact in facts)
        return "\n".join(lines)
