from __future__ import annotations

from typing import Any, Optional

from ..components.execution.sql_executor import SQLExecutor
from ..components.generation.sql_generator import SQLGenerator
from ..components.retrieval.keyword import KeywordRetriever
from ..core.base import BaseFlow
from ..core.catalog import RetrievalResult
from ..core.hooks import TraceHook
from ..core.ports import DBPort, LLMPort


class BaselineNL2SQL(BaseFlow):
    """
    End-to-end NL→SQL pipeline.

    Default pipeline: KeywordRetriever → SQLGenerator → SQLExecutor

    A custom retriever (e.g. VectorRetriever) can be injected via the
    ``retriever`` parameter, replacing the default KeywordRetriever.
    Both list[CatalogEntry] and RetrievalResult return types are supported.

    Usage::

        pipeline = BaselineNL2SQL(
            catalog=[{"name": "orders", "description": "...", "columns": {...}}],
            llm=AnthropicLLM(model="claude-sonnet-4-6"),
            db=SQLAlchemyDB("sqlite:///sample.db"),
            db_dialect="sqlite",
        )
        rows = pipeline.run("지난달 주문 건수")

    Supported ``db_dialect`` values: ``"sqlite"``, ``"postgresql"``, ``"mysql"``,
    ``"bigquery"``, ``"duckdb"``, ``"default"`` (or ``None`` for default).
    """

    def __init__(
        self,
        *,
        catalog: list[dict],
        llm: LLMPort,
        db: DBPort,
        db_dialect: Optional[str] = None,
        retriever: Optional[Any] = None,
        hook: Optional[TraceHook] = None,
    ) -> None:
        super().__init__(name="BaselineNL2SQL", hook=hook)
        self._retriever = retriever or KeywordRetriever(catalog=catalog, hook=hook)
        self._generator = SQLGenerator(llm=llm, db_dialect=db_dialect, hook=hook)
        self._executor = SQLExecutor(db=db, hook=hook)

    def _run(self, query: str) -> list[dict[str, Any]]:
        result = self._retriever(query)

        # KeywordRetriever returns list[CatalogEntry]
        # VectorRetriever  returns RetrievalResult
        if isinstance(result, RetrievalResult):
            schemas = result.schemas
            context = result.context
        else:
            schemas = result
            context = []

        sql = self._generator(query, schemas, context=context)
        return self._executor(sql)
