from __future__ import annotations

from pathlib import Path

from ...core.catalog import TextDocument
from ...core.ports import DocumentLoaderPort


class MarkdownLoader(DocumentLoaderPort):
    """
    Markdown file(s) (.md) → list[TextDocument].

    Standard library only. No external dependencies.

    - Single file: ``load("docs/revenue.md")`` → [TextDocument]
    - Directory:   ``load("docs/")``            → [TextDocument, ...]  (recursive)

    The first ``# heading`` becomes ``title``; the full file text becomes ``content``.
    Falls back to the filename stem when no heading is found.
    """

    def load(self, path: str) -> list[TextDocument]:
        p = Path(path)
        if p.is_dir():
            return [doc for f in sorted(p.rglob("*.md")) for doc in self._load_file(f)]
        return self._load_file(p)

    def _load_file(self, path: Path) -> list[TextDocument]:
        content = path.read_text(encoding="utf-8")
        title = ""
        for line in content.splitlines():
            if line.startswith("# "):
                title = line[2:].strip()
                break
        return [
            TextDocument(
                id=path.stem,
                title=title or path.stem,
                content=content,
                source=str(path),
            )
        ]
