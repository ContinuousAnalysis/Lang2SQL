from __future__ import annotations

from pathlib import Path

from ...core.catalog import TextDocument
from ...core.ports import DocumentLoaderPort


class PlainTextLoader(DocumentLoaderPort):
    """
    Plain text file(s) (.txt, etc.) → list[TextDocument].

    Standard library only. No external dependencies.

    - Single file: ``load("notes.txt")`` → [TextDocument]
    - Directory:   ``load("data/")``      → [TextDocument, ...] (recursive)

    ``title`` = filename stem, ``content`` = full file text.

    Args:
        extensions: File extensions to load. Default ``[".txt"]``.
    """

    def __init__(self, extensions: list[str] | None = None) -> None:
        self._extensions = extensions or [".txt"]

    def load(self, path: str) -> list[TextDocument]:
        p = Path(path)
        if p.is_dir():
            docs: list[TextDocument] = []
            for ext in self._extensions:
                for f in sorted(p.rglob(f"*{ext}")):
                    docs.extend(self._load_file(f))
            return docs
        return self._load_file(p)

    def _load_file(self, path: Path) -> list[TextDocument]:
        content = path.read_text(encoding="utf-8")
        return [
            TextDocument(
                id=path.stem,
                title=path.stem,
                content=content,
                source=str(path),
            )
        ]
