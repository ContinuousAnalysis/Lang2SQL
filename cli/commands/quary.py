"""자연어 질문을 SQL 쿼리로 변환하는 CLI 명령어 정의 모듈.

이 모듈은 사용자가 입력한 자연어 질문을 SQL 쿼리로 변환하여 출력하는
`query` CLI 명령어를 제공합니다.
"""

import click

from cli.utils.logger import configure_logging

logger = configure_logging()


@click.command(name="query")
@click.argument("question", type=str)
@click.option(
    "--flow",
    type=click.Choice(["baseline", "enriched"]),
    default="baseline",
    help="사용할 플로우 (기본값: baseline)",
)
@click.option(
    "--top-n",
    type=int,
    default=5,
    help="검색된 상위 테이블 수 제한 (기본값: 5)",
)
@click.option(
    "--dialect",
    default=None,
    help="SQL 방언 (예: sqlite, postgresql, mysql, bigquery, duckdb)",
)
@click.option(
    "--no-gate",
    is_flag=True,
    help="QuestionGate 비활성화 (enriched 플로우 전용)",
)
def query_command(
    question: str,
    flow: str,
    top_n: int,
    dialect: str,
    no_gate: bool,
) -> None:
    """자연어 질문을 SQL 쿼리로 변환하여 실행 결과를 출력합니다.

    환경변수(LLM_PROVIDER, EMBEDDING_PROVIDER, DB_TYPE 등)로 설정을 제어합니다.
    """
    try:
        from lang2sql.factory import (
            build_db_from_env,
            build_embedding_from_env,
            build_llm_from_env,
        )
        from lang2sql.flows import BaselineNL2SQL, EnrichedNL2SQL

        llm = build_llm_from_env()
        db = build_db_from_env()

        if flow == "baseline":
            pipeline = BaselineNL2SQL(
                catalog=[],
                llm=llm,
                db=db,
                db_dialect=dialect,
            )
        else:
            embedding = build_embedding_from_env()
            pipeline = EnrichedNL2SQL(
                catalog=[],
                llm=llm,
                db=db,
                embedding=embedding,
                db_dialect=dialect,
                gate_enabled=not no_gate,
                top_n=top_n,
            )

        rows = pipeline.run(question)
        if rows:
            import json
            print(json.dumps(rows, ensure_ascii=False, indent=2))
        else:
            print("(결과 없음)")

    except Exception as e:
        logger.error("쿼리 처리 중 오류 발생: %s", e)
        raise
