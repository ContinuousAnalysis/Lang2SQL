"""The stored unit of the semantic layer (★④).

A :class:`SemanticEntry` is one confirmed definition — a metric, dimension,
relationship, or business rule — that has landed in the semantic layer after
a user confirmed a :class:`~lang2sql.core.ports.ingestion.SemanticCandidate`
(or typed it directly via ``/define_metric``). Entries are pure data: they
carry no I/O and are addressed by ``name`` within a federation scope.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class SemanticKind(str, Enum):
    """What flavour of definition an entry holds.

    Superset of ``CandidateKind`` — candidates only ever propose METRIC,
    DIMENSION, or RULE, but the layer can also store RELATIONSHIP entries
    authored directly (e.g. join keys between tables).
    """

    METRIC = "metric"
    DIMENSION = "dimension"
    RELATIONSHIP = "relationship"
    RULE = "rule"


@dataclass
class SemanticEntry:
    """One confirmed definition stored at a single federation scope.

    ``name`` is the lookup key (unique within a scope); ``definition`` is the
    natural-language or SQL-fragment meaning injected into the system prompt.
    ``applies_to`` optionally narrows the entry to a table/column. ``source_id``
    links back to the originating document so the audit trail survives.
    """

    kind: SemanticKind
    name: str
    definition: str
    applies_to: str = ""
    source_id: str = ""
    created_by: str = ""
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


def Metric(name: str, definition: str, **kwargs: str) -> SemanticEntry:
    """Convenience builder pinning ``kind`` to METRIC."""
    return SemanticEntry(SemanticKind.METRIC, name, definition, **kwargs)


def Dimension(name: str, definition: str, **kwargs: str) -> SemanticEntry:
    """Convenience builder pinning ``kind`` to DIMENSION."""
    return SemanticEntry(SemanticKind.DIMENSION, name, definition, **kwargs)


def Relationship(name: str, definition: str, **kwargs: str) -> SemanticEntry:
    """Convenience builder pinning ``kind`` to RELATIONSHIP."""
    return SemanticEntry(SemanticKind.RELATIONSHIP, name, definition, **kwargs)


def Rule(name: str, definition: str, **kwargs: str) -> SemanticEntry:
    """Convenience builder pinning ``kind`` to RULE."""
    return SemanticEntry(SemanticKind.RULE, name, definition, **kwargs)
