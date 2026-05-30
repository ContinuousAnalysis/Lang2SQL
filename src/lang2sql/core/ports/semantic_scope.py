"""Semantic scope port — git-like federation resolution (★④).

The same term ("active user") can mean different things per team. Definitions
are stored against a :class:`Scope`; resolution walks ``Identity.scope_chain``
narrow→wide and the first hit wins. No conflicts — each scope lives in its own
branch. V1 = guild/channel/thread auto-resolution + ``/semantic show``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from ..identity import Identity, Scope

if TYPE_CHECKING:
    from ...semantic.types import SemanticEntry
    from ...semantic.layer import SemanticLayer


@runtime_checkable
class ScopeResolverPort(Protocol):
    """Resolve the effective semantic layer for an identity's scope chain."""

    async def effective_layer(self, identity: Identity) -> "SemanticLayer":
        """Merge scopes narrow→wide so the most specific definition wins."""
        ...

    async def define(self, scope: Scope, entry: "SemanticEntry") -> None:
        """Persist one definition at an explicit scope."""
        ...

    async def entries_at(self, scope: Scope) -> "list[SemanticEntry]":
        """Definitions stored exactly at ``scope`` (no inheritance)."""
        ...
