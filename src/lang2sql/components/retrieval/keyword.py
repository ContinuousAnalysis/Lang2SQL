from __future__ import annotations

from typing import Any, Optional

from ...core.base import BaseComponent
from ...core.context import RunContext
from ...core.hooks import TraceHook
from ._bm25 import _BM25Index

_DEFAULT_INDEX_FIELDS = ["name", "description", "columns"]


class KeywordRetriever(BaseComponent):
    """
    BM25-based keyword retriever over a table catalog.

    Indexes catalog entries at init time (in-memory).
    On each call, reads ``run.query`` and writes top-N matches
    into ``run.schema_selected``.

    Args:
        catalog:       List of table dicts. Each dict should have at minimum
                       ``name`` (str) and ``description`` (str).
                       Optional keys: ``columns`` (dict[str, str]), ``meta`` (dict).
        top_n:         Maximum number of results to return. Defaults to 5.
        index_fields:  Fields to index. Defaults to ["name", "description", "columns"].
                       Pass a custom list to replace the default (complete override).
        name:          Component name for tracing. Defaults to "KeywordRetriever".
        hook:          Optional TraceHook for observability.

    Example::

        retriever = KeywordRetriever(catalog=[
            {"name": "orders", "description": "주문 정보 테이블"},
        ])
        run = retriever(RunContext(query="주문 조회"))
        print(run.schema_selected)  # [{"name": "orders", ...}]
    """

    def __init__(
        self,
        *,
        catalog: list[dict[str, Any]],
        top_n: int = 5,
        index_fields: Optional[list[str]] = None,
        name: Optional[str] = None,
        hook: Optional[TraceHook] = None,
    ) -> None:
        super().__init__(name=name or "KeywordRetriever", hook=hook)
        self._catalog = catalog
        self._top_n = top_n
        self._index_fields = index_fields if index_fields is not None else _DEFAULT_INDEX_FIELDS
        self._index = _BM25Index(catalog, self._index_fields)

    def run(self, run: RunContext) -> RunContext:
        """
        Search the catalog with BM25 and store results in ``run.schema_selected``.

        Args:
            run: Current RunContext. Reads ``run.query``.

        Returns:
            The same RunContext with ``run.schema_selected`` set to a
            ranked list[dict] (BM25 score descending). Empty list if no match.
        """
        if not self._catalog:
            run.schema_selected = []
            return run

        scores = self._index.score(run.query)

        # Pair each catalog entry with its score, sort descending
        ranked = sorted(
            zip(scores, self._catalog),
            key=lambda x: x[0],
            reverse=True,
        )

        # Return up to top_n entries that have a positive score
        results = [
            entry
            for score, entry in ranked[: self._top_n]
            if score > 0.0
        ]

        run.schema_selected = results
        return run
