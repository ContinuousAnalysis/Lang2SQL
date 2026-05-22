"""Federation resolution over a :class:`SemanticStore` (★④).

Implements :class:`~lang2sql.core.ports.semantic_scope.ScopeResolverPort`. The
store holds raw per-scope definitions; this resolver walks an identity's
``scope_chain()`` (narrow→wide) and merges them so the most specific definition
of each ``name`` wins. ``define``/``entries_at`` delegate straight to the store.
"""

from __future__ import annotations

from ..core.identity import Identity, Scope
from ..semantic.layer import SemanticLayer
from ..semantic.scoped_layer import merge_scoped
from ..semantic.store import SemanticStore
from ..semantic.types import SemanticEntry


class ScopeResolver:
    """Resolve effective semantic layers, backed by a :class:`SemanticStore`."""

    def __init__(self, store: SemanticStore | None = None) -> None:
        self._store = store if store is not None else SemanticStore()

    @property
    def store(self) -> SemanticStore:
        return self._store

    async def effective_layer(self, identity: Identity) -> SemanticLayer:
        """Merge ``identity``'s scope chain narrow→wide; most specific wins."""
        scoped = [
            (scope, self._store.entries_at(scope))
            for scope in identity.scope_chain()
        ]
        return merge_scoped(scoped)

    async def define(self, scope: Scope, entry: SemanticEntry) -> None:
        """Persist one definition at an explicit scope."""
        self._store.add(scope, entry)

    async def entries_at(self, scope: Scope) -> list[SemanticEntry]:
        """Definitions stored exactly at ``scope`` (no inheritance)."""
        return self._store.entries_at(scope)
