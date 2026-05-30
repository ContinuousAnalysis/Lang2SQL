"""Pure federation merge — most specific scope wins (★④).

Given each scope's own entries ordered NARROW→WIDE (thread, channel, guild,
builtin), collapse them into one :class:`SemanticLayer`. For any ``name`` the
first (narrowest) definition encountered is authoritative; wider scopes only
contribute names the narrow scopes did not define. No I/O here — the resolver
gathers the per-scope lists and hands them in.
"""

from __future__ import annotations

from ..core.identity import Scope
from .layer import SemanticLayer
from .types import SemanticEntry


def merge_scoped(
    scoped_entries: list[tuple[Scope, list[SemanticEntry]]],
) -> SemanticLayer:
    """Merge ordered ``(scope, entries)`` pairs into one effective layer.

    ``scoped_entries`` must run narrow→wide. The first definition seen for a
    given ``name`` wins; later (wider) ones for the same name are dropped.
    """
    layer = SemanticLayer()
    seen: set[str] = set()
    for _scope, entries in scoped_entries:
        for entry in entries:
            if entry.name in seen:
                continue
            seen.add(entry.name)
            layer.add(entry)
    return layer
