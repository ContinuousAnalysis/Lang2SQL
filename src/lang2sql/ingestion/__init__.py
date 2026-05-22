"""Ingestion — document → semantic candidates via Source × Extractor (★③).

V1 wires file upload (``FileSource``) × LLM extraction (``LLMExtractor``)
through ``IngestionPipeline``. See ``core/ports/ingestion.py`` for the axis
Protocols.
"""

from __future__ import annotations

from .extractors import LLMExtractor
from .pipeline import IngestionPipeline
from .sources import FileSource

__all__ = [
    "IngestionPipeline",
    "FileSource",
    "LLMExtractor",
]
