from __future__ import annotations

from pathlib import Path

from ...core.catalog import TextDocument
from ...core.exceptions import IntegrationMissingError

try:
    import fitz as _fitz
except ImportError:
    _fitz = None  # type: ignore[assignment]


class PDFLoader:
    """
    PDF file → list[TextDocument].

    Requires pymupdf (fitz) as an optional dependency.
    Raises ``IntegrationMissingError`` if not installed.

    Produces one TextDocument per page::

        id      = "{filename}__p{page_number}"   (1-indexed)
        title   = "{filename} page {page_number}"
        content = extracted text of that page
        source  = file path

    Usage::

        from lang2sql.integrations.loaders import PDFLoader

        docs = PDFLoader().load("report.pdf")

    Installation::

        pip install pymupdf
    """

    def load(self, path: str) -> list[TextDocument]:
        if _fitz is None:
            raise IntegrationMissingError(
                "pymupdf",
                hint="pip install pymupdf",
            )
        p = Path(path)
        pdf = _fitz.open(str(p))
        docs: list[TextDocument] = []
        for i, page in enumerate(pdf, start=1):
            docs.append(
                TextDocument(
                    id=f"{p.stem}__p{i}",
                    title=f"{p.stem} page {i}",
                    content=page.get_text(),
                    source=str(p),
                )
            )
        return docs
