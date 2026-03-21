from __future__ import annotations

from typing import Any

from ...core.exceptions import IntegrationMissingError
from ...core.ports import DBPort

try:
    from sqlalchemy import create_engine, inspect as sa_inspect, text as sa_text
    from sqlalchemy.engine import Engine
except ImportError:
    create_engine = None  # type: ignore[assignment]
    sa_inspect = None  # type: ignore[assignment]
    sa_text = None  # type: ignore[assignment]
    Engine = None  # type: ignore[assignment,misc]


class SQLAlchemyDB(DBPort):
    """DBPort implementation backed by SQLAlchemy 2.x."""

    def __init__(self, url: str) -> None:
        if create_engine is None:
            raise IntegrationMissingError(
                "sqlalchemy", extra="sqlalchemy", hint="pip install sqlalchemy"
            )
        self._engine: Engine = create_engine(url)

    def execute(self, sql: str) -> list[dict[str, Any]]:
        with self._engine.connect() as conn:
            result = conn.execute(sa_text(sql))
            return [dict(row._mapping) for row in result]


_WRITE_PREFIXES = frozenset(
    {
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "ALTER",
        "CREATE",
        "TRUNCATE",
        "REPLACE",
        "MERGE",
    }
)


class SQLAlchemyExplorer:
    """DBExplorerPort implementation backed by SQLAlchemy 2.x.

    Agent가 DB 스키마를 탐색할 때 사용. DDL + 샘플 데이터를 LLM context에 직접 주입.
    """

    def __init__(self, url: str, *, schema: str | None = None) -> None:
        if create_engine is None:
            raise IntegrationMissingError(
                "sqlalchemy", extra="sqlalchemy", hint="pip install sqlalchemy"
            )
        self._engine: Engine = create_engine(url)
        self._schema = schema

    @classmethod
    def from_engine(
        cls, engine: "Engine", *, schema: str | None = None
    ) -> "SQLAlchemyExplorer":
        """기존 engine 공유용. 연결 풀 중복 방지."""
        instance = cls.__new__(cls)
        instance._engine = engine
        instance._schema = schema
        return instance

    def list_tables(self, schema: str | None = None) -> list[str]:
        """테이블 목록 반환. Agent가 DB 구조 파악 시 첫 번째 호출."""
        insp = sa_inspect(self._engine)
        return insp.get_table_names(schema=schema or self._schema)

    def get_ddl(self, table: str, *, schema: str | None = None) -> str:
        """원본 DDL 문자열 반환. 컬럼 정의, PK, FK, 제약조건 모두 포함.

        SQLite: sqlite_master에서 원본 그대로 (DEFAULT, 코멘트, 인라인 FK 모두 보존).
        그 외: SQLAlchemy CreateTable construct로 포괄적 DDL 생성.
        """
        resolved_schema = schema or self._schema
        if self._engine.dialect.name == "sqlite":
            rows = self._execute_safe(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=:table",
                {"table": table},
            )
            if rows and rows[0].get("sql"):
                return rows[0]["sql"]

        from sqlalchemy import MetaData
        from sqlalchemy import Table as SATable
        from sqlalchemy.schema import CreateTable

        metadata = MetaData()
        t = SATable(table, metadata, autoload_with=self._engine, schema=resolved_schema)
        return str(CreateTable(t).compile(self._engine))

    def sample_data(
        self, table: str, *, limit: int = 5, schema: str | None = None
    ) -> list[dict]:
        """실제 샘플 데이터 반환.

        f-string SQL 금지 — SQLAlchemy ORM select()로 identifier quoting 위임.
        dialect별 quoting 차이(PostgreSQL ", MySQL `, SQLite ")를 SQLAlchemy가 처리.
        """
        from sqlalchemy import MetaData, select
        from sqlalchemy import Table as SATable

        resolved_schema = schema or self._schema
        metadata = MetaData()
        t = SATable(table, metadata, autoload_with=self._engine, schema=resolved_schema)
        stmt = select(t).limit(limit)
        with self._engine.connect() as conn:
            result = conn.execute(stmt)
            return [dict(row._mapping) for row in result]

    def execute_read_only(self, sql: str) -> list[dict]:
        """읽기 전용 SQL 실행.

        두 겹 방어:
        1. prefix guard — 일반적인 쓰기 구문 빠른 거부 (UX)
        2. rollback-always — WITH ... DELETE 같은 CTE 우회도 실제 DB 반영 방지
        """
        first_token = sql.strip().upper().split()[0] if sql.strip() else ""
        if first_token in _WRITE_PREFIXES:
            raise ValueError(f"Write operations not allowed: {sql[:50]!r}")
        with self._engine.connect() as conn:
            result = conn.execute(sa_text(sql))
            rows = [dict(row._mapping) for row in result]
            conn.rollback()
        return rows

    def _execute_safe(self, sql: str, params: dict | None = None) -> list[dict]:
        """파라미터화 쿼리 실행 (내부용)."""
        with self._engine.connect() as conn:
            result = conn.execute(sa_text(sql), params or {})
            return [dict(row._mapping) for row in result]
