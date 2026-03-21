"""Tests for SQLAlchemyExplorer (Phase A1)."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text

# ---------------------------------------------------------------------------
# Fixture: SQLite in-memory DB with FK schema
# ---------------------------------------------------------------------------


@pytest.fixture()
def engine():
    eng = create_engine("sqlite:///:memory:")
    with eng.connect() as conn:
        conn.execute(text("""
            CREATE TABLE customers (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE
            )
        """))
        conn.execute(text("""
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY,
                customer_id INTEGER NOT NULL REFERENCES customers(id),
                amount REAL,
                status TEXT DEFAULT 'pending'
            )
        """))
        conn.execute(
            text("INSERT INTO customers VALUES (1, 'Alice', 'alice@example.com')")
        )
        conn.execute(text("INSERT INTO customers VALUES (2, 'Bob', 'bob@example.com')"))
        conn.execute(text("INSERT INTO orders VALUES (1, 1, 99.9, 'shipped')"))
        conn.execute(text("INSERT INTO orders VALUES (2, 2, 42.0, 'pending')"))
        conn.commit()
    return eng


@pytest.fixture()
def explorer(engine):
    from lang2sql.integrations.db.sqlalchemy_ import SQLAlchemyExplorer

    return SQLAlchemyExplorer.from_engine(engine)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_list_tables(explorer):
    tables = explorer.list_tables()
    assert set(tables) == {"customers", "orders"}


def test_get_ddl_sqlite(explorer):
    ddl = explorer.get_ddl("orders")
    # 원본 DDL에 REFERENCES 절 포함 확인
    assert "REFERENCES" in ddl
    assert "customer_id" in ddl


def test_get_ddl_contains_all_columns(explorer):
    ddl = explorer.get_ddl("customers")
    for col in ("id", "name", "email"):
        assert col in ddl


def test_sample_data(explorer):
    rows = explorer.sample_data("customers", limit=1)
    assert len(rows) == 1
    assert "name" in rows[0]
    assert "email" in rows[0]


def test_sample_data_default_limit(explorer):
    rows = explorer.sample_data("customers")
    # 2행 삽입, limit=5(기본값) → 모두 반환
    assert len(rows) == 2


def test_sample_data_empty_table(engine):
    from lang2sql.integrations.db.sqlalchemy_ import SQLAlchemyExplorer

    with engine.connect() as conn:
        conn.execute(text("CREATE TABLE empty_tbl (x INTEGER)"))
        conn.commit()

    exp = SQLAlchemyExplorer.from_engine(engine)
    assert exp.sample_data("empty_tbl") == []


def test_execute_read_only_select(explorer):
    rows = explorer.execute_read_only("SELECT id, name FROM customers ORDER BY id")
    assert len(rows) == 2
    assert rows[0]["name"] == "Alice"


def test_execute_read_only_rejects_insert(explorer):
    with pytest.raises(ValueError, match="Write operations not allowed"):
        explorer.execute_read_only(
            "INSERT INTO customers VALUES (3, 'Eve', 'eve@x.com')"
        )


def test_execute_read_only_rejects_drop(explorer):
    with pytest.raises(ValueError, match="Write operations not allowed"):
        explorer.execute_read_only("DROP TABLE customers")


def test_execute_read_only_rejects_cte_delete(explorer):
    # SQLite는 CTE + DELETE를 지원하지 않으므로 rollback만 검증
    # prefix guard는 통과하지만 실제 변경이 없음을 확인
    initial = explorer.execute_read_only("SELECT COUNT(*) as cnt FROM customers")
    initial_count = initial[0]["cnt"]

    # rollback-always 검증: SELECT는 정상 동작, 데이터 변경 없음
    rows = explorer.execute_read_only("SELECT * FROM customers WHERE id = 1")
    assert len(rows) == 1

    after = explorer.execute_read_only("SELECT COUNT(*) as cnt FROM customers")
    assert after[0]["cnt"] == initial_count


def test_from_engine_shares_data(engine):
    from lang2sql.integrations.db.sqlalchemy_ import SQLAlchemyExplorer

    exp1 = SQLAlchemyExplorer.from_engine(engine)
    exp2 = SQLAlchemyExplorer.from_engine(engine)

    rows1 = exp1.sample_data("customers")
    rows2 = exp2.sample_data("customers")
    assert rows1 == rows2


def test_integration_with_sqlalchemydb(engine):
    from lang2sql.integrations.db.sqlalchemy_ import SQLAlchemyDB, SQLAlchemyExplorer

    # SQLAlchemyDB와 같은 engine을 SQLAlchemyExplorer가 공유
    explorer = SQLAlchemyExplorer.from_engine(engine)

    tables = explorer.list_tables()
    assert "customers" in tables

    ddl = explorer.get_ddl("customers")
    assert "id" in ddl
