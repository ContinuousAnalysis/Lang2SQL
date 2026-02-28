from __future__ import annotations

from typing import Optional

from ..components.enrichment.context_enricher import ContextEnricher
from ..components.enrichment.question_profiler import QuestionProfiler
from ..components.execution.sql_executor import SQLExecutor
from ..components.gate.question_gate import QuestionGate
from ..components.gate.table_suitability import TableSuitabilityEvaluator
from ..components.generation.sql_generator import SQLGenerator
from ..components.retrieval.hybrid import HybridRetriever
from ..core.base import BaseFlow
from ..core.catalog import TextDocument
from ..core.exceptions import ContractError
from ..core.hooks import TraceHook
from ..core.ports import DBPort, EmbeddingPort, LLMPort


class EnrichedNL2SQL(BaseFlow):
    """
    풀 파이프라인 NL→SQL:
    QuestionGate → HybridRetriever → TableSuitabilityEvaluator
      → QuestionProfiler → ContextEnricher → SQLGenerator → SQLExecutor

    레거시 LangGraph 기반 engine/query_executor.py + graph_utils/enriched_graph.py를 대체한다.

    Args:
        catalog:      list[CatalogEntry] — 검색 대상 테이블 메타데이터.
        llm:          LLMPort — 질문 평가, SQL 생성 등에 사용.
        db:           DBPort — SQL 실행 대상 데이터베이스.
        embedding:    EmbeddingPort — 벡터 검색용 임베딩 모델.
        documents:    Optional list of business documents to index.
        db_dialect:   SQL 방언. "sqlite", "postgresql", "mysql", "bigquery", "duckdb", "default".
        gate_enabled: QuestionGate를 활성화할지 여부. Default True.
        top_n:        HybridRetriever가 반환할 최대 스키마 수. Default 5.
        hook:         TraceHook for observability.

    Usage::

        pipeline = EnrichedNL2SQL(
            catalog=[{"name": "orders", "description": "...", "columns": {...}}],
            llm=AnthropicLLM(model="claude-sonnet-4-6"),
            db=SQLAlchemyDB("sqlite:///sample.db"),
            embedding=OpenAIEmbedding(model="text-embedding-3-small"),
            db_dialect="sqlite",
        )
        rows = pipeline.run("지난달 주문 건수를 알려줘")
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
        gate_enabled: bool = True,
        top_n: int = 5,
        hook: Optional[TraceHook] = None,
    ) -> None:
        super().__init__(name="EnrichedNL2SQL", hook=hook)
        self._gate = QuestionGate(llm=llm, hook=hook) if gate_enabled else None
        self._retriever = HybridRetriever(
            catalog=catalog,
            embedding=embedding,
            documents=documents,
            top_n=top_n,
            hook=hook,
        )
        self._table_eval = TableSuitabilityEvaluator(llm=llm, hook=hook)
        self._profiler = QuestionProfiler(llm=llm, hook=hook)
        self._enricher = ContextEnricher(llm=llm, hook=hook)
        self._generator = SQLGenerator(llm=llm, db_dialect=db_dialect, hook=hook)
        self._executor = SQLExecutor(db=db, hook=hook)

    def _run(self, query: str) -> list[dict]:
        # 1. Gate (선택적): 질문이 SQL 답변 불가능하면 ContractError 발생
        if self._gate is not None:
            gate = self._gate(query)
            if not gate.suitable:
                raise ContractError(f"Query not suitable for SQL: {gate.reason}")

        # 2. Retrieval: HybridRetriever → RetrievalResult
        result = self._retriever(query)

        # 3. Table filtering: 관련도 낮은 테이블 제거
        schemas = self._table_eval(query, result.schemas)

        # 4. Profiling: 질문 특성 추출
        profile = self._profiler(query)

        # 5. Context enrichment: 보강된 질문 텍스트 생성
        enriched = self._enricher(query, schemas, profile)

        # 6. SQL generation: 보강된 컨텍스트 + 도메인 문서를 함께 전달
        sql = self._generator(query, schemas, context=[enriched] + result.context)

        # 7. Execution
        return self._executor(sql)
