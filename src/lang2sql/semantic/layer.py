"""The effective semantic layer for one resolved scope (★④).

A :class:`SemanticLayer` is a flat bag of :class:`SemanticEntry` already
resolved for a particular request — federation merging happens upstream in
:mod:`lang2sql.semantic.scoped_layer`. The harness calls :meth:`render` to
splice these definitions into the system prompt so the model prefers them over
its own assumptions.
"""

from __future__ import annotations

from .types import SemanticEntry


class SemanticLayer:
    """An ordered collection of definitions keyed by ``name``.

    Insertion order is preserved for stable rendering; :meth:`add` replaces an
    existing entry of the same ``name`` in place so later authority wins
    without reordering.
    """

    def __init__(self, entries: list[SemanticEntry] | None = None) -> None:
        self._entries: list[SemanticEntry] = list(entries or [])

    @property
    def entries(self) -> list[SemanticEntry]:
        return list(self._entries)

    def lookup(self, name: str) -> SemanticEntry | None:
        """Return the entry named ``name``, or ``None`` if absent."""
        for entry in self._entries:
            if entry.name == name:
                return entry
        return None

    def add(self, entry: SemanticEntry) -> None:
        """Add ``entry``, replacing any existing entry with the same name."""
        for i, existing in enumerate(self._entries):
            if existing.name == entry.name:
                self._entries[i] = entry
                return
        self._entries.append(entry)

    def render(self) -> str:
        """Markdown bullet list for system-prompt injection.

        Empty string when there are no entries so the caller can skip the
        section header entirely.
        """
        if not self._entries:
            return ""
        lines: list[str] = []
        for entry in self._entries:
            scope = f" (applies to {entry.applies_to})" if entry.applies_to else ""
            lines.append(
                f"- **{entry.name}** [{entry.kind.value}]: {entry.definition}{scope}"
            )
        return "\n".join(lines)
