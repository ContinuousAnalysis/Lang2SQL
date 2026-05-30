"""FileSource — the V1 Source axis (★③).

Pulls a document from an uploaded file (MD/PDF/TXT). If the caller already has
the bytes (a Discord attachment), pass them as ``blob`` and they are decoded as
utf-8; otherwise the file at ``ref`` is read from disk. v1.5 adds a URL source
implementing the same :class:`SourcePort`.
"""

from __future__ import annotations

import os

from ...core.ports.ingestion import Document


class FileSource:
    """``SourcePort`` over a local file or an in-memory blob."""

    async def fetch(self, ref: str, blob: bytes | None = None) -> Document:
        if blob is not None:
            text = blob.decode("utf-8")
        else:
            with open(ref, "r", encoding="utf-8") as handle:
                text = handle.read()
        return Document(name=os.path.basename(ref), text=text, source_id=ref)
