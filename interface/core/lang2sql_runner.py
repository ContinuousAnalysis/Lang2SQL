"""
Lang2SQL 실행 모듈.

이 모듈은 자연어로 입력된 질문을 SQL 쿼리로 변환하고,
지정된 데이터베이스 환경에서 실행하는 함수(`run_lang2sql`)를 제공합니다.
내부적으로 v2 플로우(BaselineNL2SQL / EnrichedNL2SQL)를 사용한다.
"""
from __future__ import annotations

from typing import Any


def run_lang2sql(
    query: str,
    db_dialect: str | None = None,
    top_n: int = 5,
    use_enriched: bool = False,
    catalog: list | None = None,
) -> dict[str, Any]:
    """Lang2SQL 실행 함수.

    주어진 자연어 질문을 SQL 쿼리로 변환하고 데이터베이스에서 실행한다.
    LLM, Embedding, DB는 환경변수(LLM_PROVIDER, EMBEDDING_PROVIDER, DB_TYPE 등)로
    자동 설정된다.

    Args:
        query:        사용자 입력 자연어 질문.
        db_dialect:   SQL 방언 힌트 (None이면 default 프롬프트 사용).
        top_n:        검색할 상위 테이블 수.
        use_enriched: True이면 EnrichedNL2SQL 플로우 사용.
        catalog:      CatalogEntry 목록. None이면 빈 카탈로그로 실행.

    Returns:
        dict: {"rows": list[dict], "sql": str, "error": str | None}
    """
    from lang2sql.factory import (
        build_db_from_env,
        build_embedding_from_env,
        build_llm_from_env,
    )
    from lang2sql.flows import BaselineNL2SQL, EnrichedNL2SQL

    catalog = catalog or []

    try:
        llm = build_llm_from_env()
        db = build_db_from_env()

        if use_enriched:
            embedding = build_embedding_from_env()
            pipeline = EnrichedNL2SQL(
                catalog=catalog,
                llm=llm,
                db=db,
                embedding=embedding,
                db_dialect=db_dialect,
                top_n=top_n,
            )
        else:
            pipeline = BaselineNL2SQL(
                catalog=catalog,
                llm=llm,
                db=db,
                db_dialect=db_dialect,
            )

        rows = pipeline.run(query)
        return {"rows": rows, "error": None}

    except Exception as exc:
        return {"rows": [], "error": str(exc)}
