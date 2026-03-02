# 02. Baseline 파이프라인 — 실제 DB 연결과 DB Explorer

`BaselineNL2SQL` 상세 사용법과 DB를 탐색하는 `SQLAlchemyExplorer`를 다룹니다.

---

## 사전 준비

```bash
export OPENAI_API_KEY="sk-..."
python scripts/setup_sample_db.py   # sample.db 생성
```

---

## 1) BaselineNL2SQL — 다중 테이블

```python
from lang2sql import BaselineNL2SQL
from lang2sql.integrations.db import SQLAlchemyDB
from lang2sql.integrations.llm import OpenAILLM

catalog = [
    {
        "name": "orders",
        "description": "고객 주문 정보. 주문 건수·금액·날짜 조회에 사용.",
        "columns": {
            "order_id":    "주문 고유 ID (PK)",
            "customer_id": "주문한 고객 ID (FK → customers)",
            "order_date":  "주문 일시 (TIMESTAMP)",
            "amount":      "주문 금액 (DECIMAL)",
            "status":      "주문 상태: pending / confirmed / shipped / cancelled",
        },
    },
    {
        "name": "customers",
        "description": "고객 마스터. 이름·등급·가입일 조회에 사용.",
        "columns": {
            "customer_id": "고객 고유 ID (PK)",
            "name":        "고객 이름",
            "grade":       "고객 등급: bronze / silver / gold",
            "created_at":  "가입 일시",
        },
    },
]

pipeline = BaselineNL2SQL(
    catalog=catalog,
    llm=OpenAILLM(model="gpt-4o-mini"),
    db=SQLAlchemyDB("sqlite:///sample.db"),
    db_dialect="sqlite",
)

rows = pipeline.run("지난달 gold 고객의 주문 건수")
print(rows)
```

### 지원 dialect

`db_dialect` 에 전달 가능한 값: `"sqlite"`, `"postgresql"`, `"mysql"`, `"bigquery"`, `"duckdb"`, `"default"`

---

## 2) DB Explorer — 처음 보는 DB 탐색

카탈로그를 미리 작성하지 않아도 DDL과 샘플 데이터를 바로 꺼낼 수 있습니다.
LLM에 넘길 스키마 정보를 빠르게 파악할 때 유용합니다.

### 기본 사용

```python
from lang2sql import build_explorer_from_url

exp = build_explorer_from_url("sqlite:///sample.db")

# 1) 테이블 목록
print(exp.list_tables())
# ['customers', 'orders', ...]

# 2) DDL — CREATE TABLE 원문
print(exp.get_ddl("orders"))

# 3) 샘플 데이터 (기본 5행)
print(exp.sample_data("orders"))

# 4) 읽기 전용 커스텀 쿼리
print(exp.execute_read_only("SELECT status, COUNT(*) AS cnt FROM orders GROUP BY status"))
```

### 전체 테이블 루프

```python
from lang2sql import build_explorer_from_url

exp = build_explorer_from_url("sqlite:///sample.db")

for table in exp.list_tables():
    print(f"\n=== {table} ===")
    print(exp.get_ddl(table))
    print("샘플:", exp.sample_data(table, limit=2))
```

### PostgreSQL / MySQL

URL만 바꾸면 됩니다.

```python
from lang2sql import build_explorer_from_url

# PostgreSQL (schema 범위 지정 가능)
exp = build_explorer_from_url(
    "postgresql://user:password@localhost:5432/mydb",
    schema="analytics",
)

# MySQL
exp = build_explorer_from_url("mysql+pymysql://user:password@localhost:3306/mydb")
```

### 기존 SQLAlchemyDB engine 재사용

```python
from lang2sql.integrations.db import SQLAlchemyDB, SQLAlchemyExplorer

db = SQLAlchemyDB("sqlite:///sample.db")
exp = SQLAlchemyExplorer.from_engine(db._engine)

# 같은 연결 풀을 공유
rows = db.execute("SELECT COUNT(*) AS cnt FROM orders")
ddl  = exp.get_ddl("orders")
```

### 쓰기 구문 거부

```python
exp.execute_read_only("DROP TABLE orders")
# ValueError: Write operations not allowed: 'DROP TABLE orders'

exp.execute_read_only("INSERT INTO orders VALUES (99, 1, 0, 'test')")
# ValueError: Write operations not allowed: ...
```

---

## 3) CSV 카탈로그 빠르게 구성하기

테이블이 많을 때 CSV로 카탈로그를 만드는 패턴입니다.

```python
import csv
from collections import defaultdict
from lang2sql import BaselineNL2SQL
from lang2sql.integrations.db import SQLAlchemyDB
from lang2sql.integrations.llm import OpenAILLM

# CSV 예시 (dev/table_catalog.csv)
# table_name,table_description,column_name,column_description
# orders,주문 정보 테이블,order_id,주문 ID
# orders,주문 정보 테이블,amount,결제 금액

tables: dict = defaultdict(lambda: {"desc": "", "columns": {}})
with open("dev/table_catalog.csv", newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        t = row["table_name"].strip()
        tables[t]["desc"] = row["table_description"].strip()
        tables[t]["columns"][row["column_name"].strip()] = row["column_description"].strip()

catalog = [
    {"name": t, "description": info["desc"], "columns": info["columns"]}
    for t, info in tables.items()
]

pipeline = BaselineNL2SQL(
    catalog=catalog,
    llm=OpenAILLM(model="gpt-4o-mini"),
    db=SQLAlchemyDB("sqlite:///sample.db"),
    db_dialect="sqlite",
)

rows = pipeline.run("주문 건수를 알려줘")
print(rows)
```

---

## 4) CLI 사용법

Python 코드 대신 CLI로 실행할 수 있습니다.
CLI는 환경변수(`LLM_PROVIDER`, `DB_URL` 등)로 설정을 읽으므로 `.env`를 먼저 구성합니다.

### .env 설정 (OpenAI 기준)

```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPEN_AI_LLM_MODEL=gpt-4o
EMBEDDING_PROVIDER=openai
OPEN_AI_EMBEDDING_MODEL=text-embedding-3-large
DB_URL=sqlite:///sample.db
DB_TYPE=sqlite
```

> **주의**: 코드에서 OpenAI 키는 `OPEN_AI_KEY` 또는 `OPENAI_API_KEY` 둘 다 읽습니다.
> `.env.example`을 참고해 실제 사용 변수명을 확인하세요.

### Streamlit UI 실행

```bash
lang2sql run-streamlit

# 포트 지정
lang2sql run-streamlit -p 8888
```

### CLI 쿼리 실행

```bash
# baseline 플로우 (기본값)
lang2sql query "주문 건수를 집계해줘" --flow baseline --dialect sqlite

# enriched 플로우 (BM25 + Vector + Gate)
lang2sql query "이번 달 순매출 합계" --flow enriched --dialect sqlite --top-n 5

# QuestionGate 비활성화 (enriched 전용)
lang2sql query "이번 달 순매출 합계" --flow enriched --no-gate
```

**지원 옵션:**

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--flow` | `baseline` | `baseline` 또는 `enriched` |
| `--dialect` | `None` | SQL 방언 (sqlite, postgresql, mysql 등) |
| `--top-n` | `5` | 검색할 최대 테이블 수 |
| `--no-gate` | `False` | QuestionGate 비활성화 (enriched 전용) |

> **참고**: CLI의 `--flow hybrid`는 없습니다. 하이브리드 검색은 Python API(`HybridNL2SQL`)를 사용하세요.

---

## 다음 단계

벡터 검색으로 검색 품질을 높이려면 → [03-vector-search.md](./03-vector-search.md)
