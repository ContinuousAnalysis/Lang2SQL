"""InjectAllRecall — the V1 Recall axis (★②).

The simplest possible strategy: surface every fact the owner has, ignoring the
query entirely. Good enough while fact counts are tiny. v1.5 replaces this with
keyword matching and v2 with vector similarity — same :class:`RecallPort`.
"""

from __future__ import annotations

from ...core.ports.memory import Fact, StorePort


class InjectAllRecall:
    """``RecallPort`` that returns all of an owner's facts unfiltered."""

    async def recall(self, owner: str, query: str, store: StorePort) -> list[Fact]:
        return await store.all(owner)
