"""In-memory storage of semantic definitions, keyed by scope (★④).

V1 keeps everything in a process-local dict — SQLite persistence is deferred
(v1.5). The store is intentionally dumb: it knows nothing about inheritance or
resolution, only "here are the entries authored exactly at this scope".
Resolution lives in :mod:`lang2sql.tenancy.scope_resolver`.
"""

from __future__ import annotations

from ..core.identity import Scope
from .types import SemanticEntry


class SemanticStore:
    """Maps ``str(scope)`` → the entries defined exactly at that scope."""

    def __init__(self) -> None:
        self._by_scope: dict[str, list[SemanticEntry]] = {}

    def add(self, scope: Scope, entry: SemanticEntry) -> None:
        """Store ``entry`` at ``scope``, replacing a same-named entry there."""
        bucket = self._by_scope.setdefault(str(scope), [])
        for i, existing in enumerate(bucket):
            if existing.name == entry.name:
                bucket[i] = entry
                return
        bucket.append(entry)

    def entries_at(self, scope: Scope) -> list[SemanticEntry]:
        """Entries authored exactly at ``scope`` (no inheritance)."""
        return list(self._by_scope.get(str(scope), []))
