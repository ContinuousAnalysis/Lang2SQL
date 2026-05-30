"""Expand a metric name to its definition (★④, minimal V1).

V1 deliberately does the simplest useful thing: resolve a name against an
effective :class:`SemanticLayer` and hand back the stored definition string.
Real composition — substituting nested metric references, stitching dimension
filters, emitting a SQL fragment — is later work and is flagged inline.
"""

from __future__ import annotations

from .layer import SemanticLayer


class SQLComposer:
    """Resolve metric/dimension names against a resolved semantic layer."""

    def __init__(self, layer: SemanticLayer) -> None:
        self._layer = layer

    def expand(self, name: str) -> str | None:
        """Return the definition string for ``name``, or ``None`` if unknown.

        TODO(v1.5): real composition — recursively expand nested references and
        emit a SQL fragment rather than the raw stored definition.
        """
        entry = self._layer.lookup(name)
        return entry.definition if entry is not None else None
