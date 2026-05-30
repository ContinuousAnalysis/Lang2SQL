"""Semantic federation layer (★④) — definitions, scoping, composition."""

from __future__ import annotations

from .layer import SemanticLayer
from .scoped_layer import merge_scoped
from .sql_composer import SQLComposer
from .store import SemanticStore
from .types import (
    Dimension,
    Metric,
    Relationship,
    Rule,
    SemanticEntry,
    SemanticKind,
)

__all__ = [
    "SemanticLayer",
    "merge_scoped",
    "SQLComposer",
    "SemanticStore",
    "SemanticEntry",
    "SemanticKind",
    "Metric",
    "Dimension",
    "Relationship",
    "Rule",
]
