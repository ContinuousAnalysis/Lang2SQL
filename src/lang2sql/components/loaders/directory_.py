from __future__ import annotations

from pathlib import Path

from ...core.catalog import TextDocument
from ...core.ports import DocumentLoaderPort
from .markdown_ import MarkdownLoader
from .plaintext_ import PlainTextLoader


class DirectoryLoader:
    """
    Recursively loads a directory by dispatching each file to the loader
    registered for its extension.

    Default mapping::

        .md  → MarkdownLoader
        .txt → PlainTextLoader

    Custom loaders can be added or override defaults::

        from lang2sql.integrations.loaders import PDFLoader

        docs = DirectoryLoader(
            "docs/",
            loaders={".md": MarkdownLoader(), ".pdf": PDFLoader()},
        ).load()

    Args:
        path:    Directory path to load.
        loaders: Mapping of lowercase extension → DocumentLoaderPort.
                 Defaults to ``{".md": MarkdownLoader(), ".txt": PlainTextLoader()}``.
    """

    def __init__(
        self,
        path: str,
        loaders: dict[str, DocumentLoaderPort] | None = None,
    ) -> None:
        self._path = Path(path)
        self._loaders: dict[str, DocumentLoaderPort] = loaders or {
            ".md": MarkdownLoader(),
            ".txt": PlainTextLoader(),
        }

    def load(self) -> list[TextDocument]:
        """Recursively walk the directory and load all files with a registered extension."""
        docs: list[TextDocument] = []
        for file in sorted(self._path.rglob("*")):
            if not file.is_file():
                continue
            loader = self._loaders.get(file.suffix.lower())
            if loader is None:
                continue
            docs.extend(loader.load(str(file)))
        return docs
