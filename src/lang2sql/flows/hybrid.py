from __future__ import annotations

from typing import Optional

from ..components.execution.sql_executor import SQLExecutor
from ..components.generation.sql_generator import SQLGenerator
from ..components.retrieval.hybrid import HybridRetriever
from ..core.base import BaseFlow
from ..core.catalog import TextDocument
from ..core.hooks import TraceHook
from ..core.ports import DBPort, EmbeddingPort, LLMPort


class HybridNL2SQL(BaseFlow):
    """
    NL→SQL pipeline backed by BM25 + vector hybrid retrieval.

    Provides higher retrieval quality than ``BaselineNL2SQL`` with only the
    addition of an ``embedding`` parameter.

    Pipeline: HybridRetriever → SQLGenerator → SQLExecutor

    Args:
        catalog:    List of CatalogEntry dicts.
        llm:        LLMPort implementation.
        db:         DBPort implementation.
        embedding:  EmbeddingPort implementation.
        documents:  Optional list of business documents to index.
        db_dialect: SQL dialect. Supported values: ``"sqlite"``, ``"postgresql"``,
                    ``"mysql"``, ``"bigquery"``, ``"duckdb"``, ``"default"``
                    (or ``None`` for default).
        top_n:      Maximum number of schemas to return. Default 5.
        hook:       TraceHook for observability.

    Usage::

        pipeline = HybridNL2SQL(
            catalog=[{"name": "orders", "description": "...", "columns": {...}}],
            llm=AnthropicLLM(model="claude-sonnet-4-6"),
            db=SQLAlchemyDB("sqlite:///sample.db"),
            embedding=OpenAIEmbedding(model="text-embedding-3-small"),
            db_dialect="sqlite",
        )
        rows = pipeline.run("How many orders last month?")
    """

    def __init__(
        self,
        *,
        catalog: list[dict],
        llm: LLMPort,
        db: DBPort,
        embedding: EmbeddingPort,
        documents: Optional[list[TextDocument]] = None,
        db_dialect: Optional[str] = None,
        top_n: int = 5,
        hook: Optional[TraceHook] = None,
    ) -> None:
        super().__init__(name="HybridNL2SQL", hook=hook)
        self._retriever = HybridRetriever(
            catalog=catalog,
            embedding=embedding,
            documents=documents,
            top_n=top_n,
            hook=hook,
        )
        self._generator = SQLGenerator(llm=llm, db_dialect=db_dialect, hook=hook)
        self._executor  = SQLExecutor(db=db, hook=hook)

    def _run(self, query: str) -> list[dict]:
        result = self._retriever(query)          # RetrievalResult
        sql    = self._generator(query, result.schemas, context=result.context)
        return self._executor(sql)
