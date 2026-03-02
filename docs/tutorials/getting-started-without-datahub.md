## DataHub 없이 시작하기 (튜토리얼)

이 문서는 DataHub 없이도 Lang2SQL을 바로 사용하기 위한 최소 절차를 설명합니다.
CSV로 테이블/컬럼 설명을 준비해 FAISS 또는 pgvector에 적재한 뒤 Lang2SQL을 실행합니다.

### 0) 준비

```bash
# 소스 클론
git clone https://github.com/CausalInferenceLab/lang2sql.git
cd lang2sql

# (권장) uv 사용
uv venv --python 3.11
source .venv/bin/activate
uv pip install -e .

# (대안) pip 사용
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 1) .env 최소 설정 (OpenAI 기준)

```bash
# LLM/임베딩
LLM_PROVIDER=openai
OPEN_AI_KEY=sk-...                # OpenAI API Key (주의: OPENAI_API_KEY가 아니라 OPEN_AI_KEY)
OPEN_AI_LLM_MODEL=gpt-4o          # 또는 gpt-4.1 등
EMBEDDING_PROVIDER=openai
OPEN_AI_EMBEDDING_MODEL=text-embedding-3-large  # 권장

# DB 타입
DB_TYPE=clickhouse
```

중요: 코드상 OpenAI 키는 `OPEN_AI_KEY` 환경변수를 사용합니다. `.example.env`의 `OPENAI_API_KEY`는 사용되지 않으니 혼동에 주의하세요.

### 2) 테이블/컬럼 메타데이터 준비 (CSV 예시)

`dev/table_catalog.csv` 파일을 생성합니다.

```csv
table_name,table_description,column_name,column_description
customers,고객 정보 테이블,customer_id,고객 고유 ID
customers,고객 정보 테이블,name,고객 이름
customers,고객 정보 테이블,created_at,가입 일시
orders,주문 정보 테이블,order_id,주문 ID
orders,주문 정보 테이블,customer_id,주문 고객 ID
orders,주문 정보 테이블,amount,결제 금액
orders,주문 정보 테이블,status,주문 상태
```

### 3) FAISS 인덱스 생성 (로컬)

`dev/create_faiss.py` 파일을 실행합니다: `python dev/create_faiss.py`

```python
"""
dev/create_faiss.py

CSV 파일에서 테이블과 컬럼 정보를 불러와 OpenAI 임베딩으로 벡터화한 뒤,
FAISSVectorStore 인덱스를 생성하고 로컬 디렉토리에 저장한다.

환경 변수:
    OPEN_AI_KEY: OpenAI API 키
    OPEN_AI_EMBEDDING_MODEL: 사용할 임베딩 모델 이름

출력:
    OUTPUT_DIR 경로에 FAISS 인덱스 저장 (catalog.faiss)
"""

import csv
import os
from collections import defaultdict

from dotenv import load_dotenv
from lang2sql import CatalogChunker, VectorRetriever
from lang2sql.integrations.embedding import OpenAIEmbedding
from lang2sql.integrations.vectorstore import FAISSVectorStore

load_dotenv()

# CSV 파일 경로
CSV_PATH = "./dev/table_catalog.csv"
# .env의 VECTORDB_LOCATION과 동일하게 맞추세요
OUTPUT_DIR = "./dev/table_info_db"

# CSV → CatalogEntry 변환
tables: dict = defaultdict(lambda: {"desc": "", "columns": {}})
with open(CSV_PATH, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        t = row["table_name"].strip()
        tables[t]["desc"] = row["table_description"].strip()
        col = row["column_name"].strip()
        col_desc = row["column_description"].strip()
        tables[t]["columns"][col] = col_desc

catalog = [
    {"name": t, "description": info["desc"], "columns": info["columns"]}
    for t, info in tables.items()
]

# 청킹 → 임베딩 → 저장
chunks = CatalogChunker().split(catalog)
store = FAISSVectorStore(index_path=f"{OUTPUT_DIR}/catalog.faiss")
os.makedirs(OUTPUT_DIR, exist_ok=True)

VectorRetriever.from_chunks(
    chunks,
    embedding=OpenAIEmbedding(
        model=os.getenv("OPEN_AI_EMBEDDING_MODEL", "text-embedding-3-large"),
        api_key=os.getenv("OPEN_AI_KEY"),
    ),
    vectorstore=store,
)
store.save()
print(f"FAISS index saved to: {OUTPUT_DIR}/catalog.faiss")
```

### 4) 실행

v2 CLI는 외부 벡터 인덱스 경로를 인수로 받지 않습니다.
앞서 생성한 FAISS 인덱스를 활용하려면 Python API로 파이프라인을 직접 구성합니다.

```python
# run_query.py
import os
from dotenv import load_dotenv
from lang2sql import CatalogChunker, VectorRetriever
from lang2sql.integrations.db import SQLAlchemyDB
from lang2sql.integrations.embedding import OpenAIEmbedding
from lang2sql.integrations.llm import OpenAILLM
from lang2sql.integrations.vectorstore import FAISSVectorStore
from lang2sql.flows.hybrid import HybridNL2SQL

load_dotenv()

INDEX_DIR = "./dev/table_info_db"
embedding = OpenAIEmbedding(
    model=os.getenv("OPEN_AI_EMBEDDING_MODEL", "text-embedding-3-large"),
    api_key=os.getenv("OPEN_AI_KEY"),
)

# FAISS 인덱스 로드 후 파이프라인 구성
store = FAISSVectorStore.load(f"{INDEX_DIR}/catalog.faiss")

pipeline = HybridNL2SQL(
    catalog=[],          # FAISS에 이미 인덱싱돼 있으므로 빈 리스트
    llm=OpenAILLM(model=os.getenv("OPEN_AI_LLM_MODEL", "gpt-4o"), api_key=os.getenv("OPEN_AI_KEY")),
    db=SQLAlchemyDB(os.getenv("DB_URL", "sqlite:///sample.db")),
    embedding=embedding,
    db_dialect=os.getenv("DB_TYPE", "sqlite"),
)

rows = pipeline.run("주문 수를 집계하는 SQL을 만들어줘")
print(rows)
```

Streamlit UI:

```bash
lang2sql run-streamlit
```

CLI (카탈로그 없이 baseline만 가능):

```bash
lang2sql query "주문 수를 집계해줘" --flow baseline --dialect sqlite
```

### 5) (선택) pgvector로 적재하기

`dev/create_pgvector.py` 파일을 실행합니다: `python dev/create_pgvector.py`

pgvector를 사용하려면 PostgreSQL에 pgvector 확장이 설치되어 있어야 합니다.
아래 중 하나를 선택하세요:

**방법 A — Docker (로컬 테스트용, 가장 빠름)**

```bash
docker run -d \
  -e POSTGRES_USER=pgvector \
  -e POSTGRES_PASSWORD=pgvector \
  -e POSTGRES_DB=postgres \
  -p 5432:5432 \
  pgvector/pgvector:pg16
```

**방법 B — 기존 PostgreSQL 서버에 확장 설치**

```sql
-- psql 또는 DBeaver 등에서 실행
CREATE EXTENSION IF NOT EXISTS vector;
```

**방법 C — 클라우드 관리형 서비스 (별도 설치 불필요)**

- [Supabase](https://supabase.com/) — 무료 플랜에서 pgvector 기본 지원
- AWS RDS PostgreSQL 15+ — 파라미터 그룹에서 `pgvector` 활성화
- Azure Database for PostgreSQL Flexible Server — 확장 목록에서 활성화

```python
"""
dev/create_pgvector.py

CSV 파일에서 테이블과 컬럼 정보를 불러와 OpenAI 임베딩으로 벡터화한 뒤,
pgvector에 적재한다. ON CONFLICT upsert를 지원하므로 재실행 시 중복 없음.

환경 변수:
    OPEN_AI_KEY: OpenAI API 키
    OPEN_AI_EMBEDDING_MODEL: 사용할 임베딩 모델 이름
    VECTORDB_LOCATION: pgvector 연결 문자열
    PGVECTOR_COLLECTION: pgvector 테이블 이름
"""

import csv
import os
from collections import defaultdict

from dotenv import load_dotenv
from lang2sql import CatalogChunker, VectorRetriever
from lang2sql.integrations.embedding import OpenAIEmbedding
from lang2sql.integrations.vectorstore import PGVectorStore

load_dotenv()

# CSV 파일 경로
CSV_PATH = "./dev/table_catalog.csv"
CONN = os.getenv("VECTORDB_LOCATION", "postgresql://pgvector:pgvector@localhost:5432/postgres")
TABLE = os.getenv("PGVECTOR_COLLECTION", "table_info_db")

# CSV → CatalogEntry 변환
tables: dict = defaultdict(lambda: {"desc": "", "columns": {}})
with open(CSV_PATH, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        t = row["table_name"].strip()
        tables[t]["desc"] = row["table_description"].strip()
        col = row["column_name"].strip()
        col_desc = row["column_description"].strip()
        tables[t]["columns"][col] = col_desc

catalog = [
    {"name": t, "description": info["desc"], "columns": info["columns"]}
    for t, info in tables.items()
]

# 청킹 → 임베딩 → pgvector 적재
chunks = CatalogChunker().split(catalog)
store = PGVectorStore(connection=CONN, table_name=TABLE)

VectorRetriever.from_chunks(
    chunks,
    embedding=OpenAIEmbedding(
        model=os.getenv("OPEN_AI_EMBEDDING_MODEL", "text-embedding-3-large"),
        api_key=os.getenv("OPEN_AI_KEY"),
    ),
    vectorstore=store,
)
print(f"pgvector collection populated: {TABLE}")
```

