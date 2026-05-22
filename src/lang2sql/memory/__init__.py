"""Memory — Hermes 3-axis split (Store / Recall / Extractor) plus service (★②).

V1 wires the simplest combination: in-memory store, inject-all recall, manual
extractor. See ``core/ports/memory.py`` for the axis Protocols.
"""

from __future__ import annotations

from .extractors import ManualExtractor
from .recall import InjectAllRecall
from .service import MemoryService
from .stores import InMemoryStore

__all__ = [
    "MemoryService",
    "InMemoryStore",
    "InjectAllRecall",
    "ManualExtractor",
]
