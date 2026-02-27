# 벡터 저장소 백엔드 가이드 — InMemory / FAISS / pgvector

> **버전**: lang2sql v0.3.0
> **업데이트**: 2026-02-27

---

## 목차

1. [세 가지 백엔드 비교](#1-세-가지-백엔드-비교)
2. [의존성 — 별도 설치 불필요](#2-의존성--별도-설치-불필요)
3. [InMemoryVectorStore — 기본값](#3-inmemoryvectorstore--기본값)
4. [FAISSVectorStore — 로컬 파일 영속성](#4-faissvectorstore--로컬-파일-영속성)
5. [PGVectorStore — PostgreSQL 영속성](#5-pgvectorstore--postgresql-영속성)
6. [백엔드 교체 방법](#6-백엔드-교체-방법)
7. [커스텀 벡터 저장소 직접 구현하기](#7-커스텀-벡터-저장소-직접-구현하기)
8. [전체 체크리스트 — API 키 없이 실행](#8-전체-체크리스트--api-키-없이-실행)

---

## 1. 세 가지 백엔드 비교

| | `InMemoryVectorStore` | `FAISSVectorStore` | `PGVectorStore` |
|---|---|---|---|
| **저장 위치** | 메모리 (휘발성) | 로컬 파일 (`.faiss` + `.meta`) | PostgreSQL DB |
| **영속성** | 없음 — 재시작 시 소멸 | 있음 — 파일로 저장/로드 | 있음 — DB에 영구 저장 |
| **Upsert** | true upsert (dict 기반) | append-only (동일 id 중복 주의) | true upsert (ON CONFLICT) |
| **멀티 서버** | 불가 | 불가 (파일 단일 접근) | 가능 |
| **권장 규모** | < 50k chunks | < 500k chunks | 500k+ chunks |
| **추가 설치** | 불필요 | 불필요 (기본 포함) | 불필요 (기본 포함) |
| **적합한 환경** | 개발/테스트, 소규모 | 단일 서버 운영, 중규모 | 팀 공유, 대규모 운영 |

---

## 2. 의존성 — 별도 설치 불필요

세 백엔드 모두 `pip install lang2sql` 한 번으로 설치됩니다.
`pyproject.toml`의 기본 의존성(`dependencies`)에 포함되어 있습니다.

| 패키지 | 고정 버전 | 역할 |
|--------|----------|------|
| `numpy` | `<2.0` | InMemoryVectorStore 행렬 연산 |
| `faiss-cpu` | `==1.10.0` | FAISSVectorStore 인덱스 엔진 |
| `psycopg2-binary` | `>=2.9.10,<3.0.0` | PGVectorStore PostgreSQL 연결 |
| `pgvector` | `==0.3.6` | PGVectorStore `vector` 타입 직렬화 |

> **GPU 가속이 필요한 경우**: `faiss-cpu`를 직접 `faiss-gpu`로 교체할 수 있습니다.
> pyproject.toml의 `faiss-cpu==1.10.0`을 `faiss-gpu==1.10.0`으로 변경 후 `uv sync`.

---

## 3. InMemoryVectorStore — 기본값

numpy 기반 브루트 포스 코사인 유사도. `vectorstore=` 를 생략하면 자동으로 사용됩니다.

**특징:**
- true upsert — 동일 chunk_id를 두 번 넣으면 덮어씀
- 검색 시 매번 행렬 재구성 (수만 벡터까지 충분히 빠름)
- 프로세스 종료 시 인덱스 소멸

```python
from lang2sql import VectorRetriever, CatalogEntry
from lang2sql.integrations.embedding import OpenAIEmbedding

CATALOG: list[CatalogEntry] = [
    {
        "name": "orders",
        "description": "고객 주문 정보",
        "columns": {"order_id": "PK", "amount": "금액", "status": "상태"},
    },
]

# vectorstore= 생략 → InMemoryVectorStore 자동 사용
retriever = VectorRetriever.from_sources(
    catalog=CATALOG,
    embedding=OpenAIEmbedding(),
)

result = retriever("주문 건수")
print(result.schemas)
```

---

## 4. FAISSVectorStore — 로컬 파일 영속성

Facebook AI Research의 벡터 검색 라이브러리.
`IndexFlatIP` + L2 정규화로 정확한 코사인 유사도를 계산합니다.

### 4-1. 기본 사용법 — from_sources()

```python
from lang2sql import VectorRetriever
from lang2sql.integrations.vectorstore import FAISSVectorStore
from lang2sql.integrations.embedding import OpenAIEmbedding

store = FAISSVectorStore(index_path="./index/catalog.faiss")

retriever = VectorRetriever.from_sources(
    catalog=CATALOG,
    embedding=OpenAIEmbedding(),
    vectorstore=store,           # ← FAISSVectorStore 주입
)

# 인덱스를 파일로 저장
store.save()
# → ./index/catalog.faiss       (FAISS 바이너리)
# → ./index/catalog.faiss.meta  (chunk id 목록 JSON)
```

### 4-2. 명시적 파이프라인 — from_chunks()

```python
from lang2sql import VectorRetriever, CatalogChunker, RecursiveCharacterChunker
from lang2sql import TextDocument
from lang2sql.integrations.vectorstore import FAISSVectorStore
from lang2sql.integrations.embedding import OpenAIEmbedding

embedding = OpenAIEmbedding()
store = FAISSVectorStore(index_path="./index/catalog.faiss")

DOCS: list[TextDocument] = [
    {
        "id": "revenue_def",
        "title": "매출 정의",
        "content": "매출은 취소 주문을 제외한 순매출 기준이다.",
        "source": "docs/revenue.md",
    },
]

chunks = (
    CatalogChunker().split(CATALOG) +
    RecursiveCharacterChunker(chunk_size=800, chunk_overlap=80).split(DOCS)
)

retriever = VectorRetriever.from_chunks(
    chunks,
    embedding=embedding,
    vectorstore=store,
)

store.save()
```

### 4-3. 재시작 시 로드

```python
from lang2sql.integrations.vectorstore import FAISSVectorStore
from lang2sql import VectorRetriever
from lang2sql.integrations.embedding import OpenAIEmbedding

# 파일에서 바로 로드 — 임베딩/인덱싱 없이 즉시 검색 가능
store = FAISSVectorStore.load("./index/catalog.faiss")

# registry는 from_chunks()가 자동 복원 불가 → 재인덱싱 필요
# 실전에서는 프로세스 시작 시 from_sources()를 다시 실행하는 패턴 권장
retriever = VectorRetriever.from_sources(
    catalog=CATALOG,
    embedding=OpenAIEmbedding(),
    vectorstore=store,   # 이미 채워진 store — upsert() 추가로 호출됨 (append)
)
```

> **append-only 제한**: `FAISSVectorStore`는 동일 chunk_id를 두 번 upsert하면
> FAISS 인덱스에 두 개의 항목이 생깁니다. 깨끗한 인덱스가 필요하면
> 새 `FAISSVectorStore()` 인스턴스로 처음부터 인덱싱하세요.

### 4-4. save/load 예외 처리

```python
# index_path 없이 생성한 경우 save()는 경로 필요
store = FAISSVectorStore()
store.upsert(["a"], [[1.0, 0.0]])
store.save("./index/catalog.faiss")      # 경로 직접 지정

# upsert() 전에 save() 호출 → RuntimeError
store_empty = FAISSVectorStore(index_path="./out.faiss")
store_empty.save()   # RuntimeError: Cannot save before any upsert() call.

# 존재하지 않는 파일 로드 → FileNotFoundError
FAISSVectorStore.load("./nonexistent.faiss")   # FileNotFoundError
```

---

## 5. PGVectorStore — PostgreSQL 영속성

PostgreSQL의 `pgvector` 확장을 사용합니다.
`ON CONFLICT DO UPDATE` true upsert로 중복 없이 멱등 인덱싱이 가능합니다.

### 5-1. PostgreSQL 빠른 시작 (Docker)

```bash
docker run -d \
  --name pgvector \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  pgvector/pgvector:pg16
```

### 5-2. 기본 사용법 — from_sources()

```python
from lang2sql import VectorRetriever
from lang2sql.integrations.vectorstore import PGVectorStore
from lang2sql.integrations.embedding import OpenAIEmbedding

store = PGVectorStore(
    connection="postgresql://postgres:postgres@localhost:5432/postgres",
    table_name="lang2sql_vectors",   # 자동 생성됨
)

retriever = VectorRetriever.from_sources(
    catalog=CATALOG,
    embedding=OpenAIEmbedding(),
    vectorstore=store,               # ← PGVectorStore 주입
)
# → upsert() 시점에 테이블이 없으면 자동 생성
# → 같은 chunk_id를 다시 upsert하면 덮어씀 (true upsert)
```

### 5-3. 명시적 파이프라인 — from_chunks()

```python
from lang2sql import VectorRetriever, CatalogChunker, RecursiveCharacterChunker
from lang2sql.integrations.vectorstore import PGVectorStore
from lang2sql.integrations.embedding import OpenAIEmbedding

store = PGVectorStore(
    connection="postgresql://postgres:postgres@localhost:5432/postgres",
    table_name="lang2sql_vectors",
)

chunks = (
    CatalogChunker().split(CATALOG) +
    RecursiveCharacterChunker().split(DOCS)
)

retriever = VectorRetriever.from_chunks(
    chunks,
    embedding=OpenAIEmbedding(),
    vectorstore=store,
)
# save() 없음 — upsert()마다 DB에 즉시 반영
```

### 5-4. 멱등 재인덱싱

같은 카탈로그로 여러 번 인덱싱해도 중복이 생기지 않습니다.

```python
# 1차 실행
retriever = VectorRetriever.from_sources(
    catalog=CATALOG, embedding=embedding, vectorstore=store
)

# 2차 실행 (카탈로그 변경 후) — 동일 chunk_id는 embedding이 갱신됨
retriever = VectorRetriever.from_sources(
    catalog=UPDATED_CATALOG, embedding=embedding, vectorstore=store
)
# DB에 중복 없이 덮어써짐 (ON CONFLICT DO UPDATE)
```

### 5-5. 자동 테이블 구조

첫 `upsert()` 시 아래 DDL이 실행됩니다:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS lang2sql_vectors (
    id        TEXT PRIMARY KEY,
    embedding vector(1536)   -- 임베딩 모델 차원에 따라 자동 결정
);
```

---

## 6. 백엔드 교체 방법

`vectorstore=` 파라미터만 바꾸면 됩니다. 나머지 파이프라인은 변경 없습니다.

```python
from lang2sql import VectorRetriever
from lang2sql.integrations.vectorstore import (
    InMemoryVectorStore,
    FAISSVectorStore,
    PGVectorStore,
)
from lang2sql.integrations.embedding import OpenAIEmbedding

embedding = OpenAIEmbedding()

# ① InMemory (기본값)
retriever = VectorRetriever.from_sources(
    catalog=CATALOG, embedding=embedding
)

# ② FAISS — vectorstore= 한 줄 교체
retriever = VectorRetriever.from_sources(
    catalog=CATALOG,
    embedding=embedding,
    vectorstore=FAISSVectorStore(index_path="./index/catalog.faiss"),
)

# ③ pgvector — vectorstore= 한 줄 교체
retriever = VectorRetriever.from_sources(
    catalog=CATALOG,
    embedding=embedding,
    vectorstore=PGVectorStore(
        connection="postgresql://postgres:postgres@localhost:5432/postgres"
    ),
)
```

---

## 7. 커스텀 벡터 저장소 직접 구현하기

`VectorStorePort` Protocol을 만족하는 클래스를 만들면 됩니다.
Chroma, Qdrant, Weaviate 등 어떤 벡터 DB든 연결 가능합니다.

```python
from lang2sql import VectorStorePort   # Protocol

class ChromaVectorStore:
    """Chroma를 lang2sql VectorStorePort에 연결하는 어댑터."""

    def __init__(self, collection_name: str = "lang2sql"):
        import chromadb
        self._client = chromadb.Client()
        self._col    = self._client.get_or_create_collection(collection_name)

    def upsert(self, ids: list[str], vectors: list[list[float]]) -> None:
        self._col.upsert(ids=ids, embeddings=vectors)

    def search(self, vector: list[float], k: int) -> list[tuple[str, float]]:
        results = self._col.query(query_embeddings=[vector], n_results=k)
        ids   = results["ids"][0]
        dists = results["distances"][0]
        return [(id_, 1.0 - dist) for id_, dist in zip(ids, dists)]


# 사용
retriever = VectorRetriever.from_sources(
    catalog=CATALOG,
    embedding=OpenAIEmbedding(),
    vectorstore=ChromaVectorStore("my_catalog"),
)
```

구현해야 할 메서드는 두 개뿐입니다:

| 메서드 | 시그니처 | 역할 |
|--------|---------|------|
| `upsert` | `(ids: list[str], vectors: list[list[float]]) -> None` | 벡터 저장 |
| `search` | `(vector: list[float], k: int) -> list[tuple[str, float]]` | 유사도 검색 → `(chunk_id, score)`, score 높을수록 유사 |

---

## 8. 전체 체크리스트 — API 키 없이 실행

아래 코드는 `FakeEmbedding`으로 API 키 없이 세 백엔드를 모두 검증합니다.
pgvector 테스트는 `TEST_POSTGRES_URL` 환경변수가 있을 때만 실행됩니다.

```python
"""
벡터 저장소 백엔드 전체 체크리스트
API 키 없이 FakeEmbedding으로 실행 가능합니다.

실행:
    python docs/tutorials/vector-store-backends.md  # ← 이 블록만 별도 .py로 저장 후 실행

pgvector 테스트 포함:
    TEST_POSTGRES_URL="postgresql://postgres:postgres@localhost:5432/postgres" \\
        python check_backends.py
"""

import os

# ── 공통 픽스처 ────────────────────────────────────────────────────────────────

class FakeEmbedding:
    """테스트용 고정 벡터 임베딩. 4차원 단위벡터를 반환합니다."""
    def embed_query(self, text: str) -> list[float]:
        return [1.0, 0.0, 0.0, 0.0]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0, 0.0, 0.0]] * len(texts)


from lang2sql import CatalogEntry, TextDocument, VectorRetriever
from lang2sql import CatalogChunker, RecursiveCharacterChunker

CATALOG: list[CatalogEntry] = [
    {
        "name": "orders",
        "description": "고객 주문 정보 테이블",
        "columns": {"order_id": "PK", "amount": "금액", "status": "상태"},
    },
    {
        "name": "customers",
        "description": "고객 마스터 데이터",
        "columns": {"customer_id": "PK", "name": "이름", "grade": "등급"},
    },
]

DOCS: list[TextDocument] = [
    {
        "id": "revenue_def",
        "title": "매출 정의",
        "content": "매출은 취소 주문을 제외한 순매출 기준이다.",
        "source": "docs/revenue.md",
    },
]

embedding = FakeEmbedding()


# ── 1. InMemoryVectorStore ─────────────────────────────────────────────────────

print("=" * 50)
print("1. InMemoryVectorStore")

from lang2sql.integrations.vectorstore import InMemoryVectorStore

retriever = VectorRetriever.from_sources(
    catalog=CATALOG,
    embedding=embedding,
    # vectorstore= 생략 → InMemoryVectorStore 자동 사용
)
result = retriever("주문 건수")
assert isinstance(result.schemas, list)
assert len(result.schemas) > 0
print(f"   schemas: {[s['name'] for s in result.schemas]}")
print("   ✓ InMemoryVectorStore 정상")


# ── 2. FAISSVectorStore ────────────────────────────────────────────────────────

print("\n2. FAISSVectorStore")

import tempfile, pathlib

faiss = __import__("faiss")  # 없으면 ImportError → 아래 try/except
try:
    from lang2sql.integrations.vectorstore import FAISSVectorStore

    with tempfile.TemporaryDirectory() as tmpdir:
        index_path = str(pathlib.Path(tmpdir) / "catalog.faiss")

        # 2-a. from_sources
        store = FAISSVectorStore(index_path=index_path)
        retriever_f = VectorRetriever.from_sources(
            catalog=CATALOG,
            embedding=embedding,
            vectorstore=store,
        )
        result_f = retriever_f("주문 건수")
        assert len(result_f.schemas) > 0
        print(f"   from_sources schemas: {[s['name'] for s in result_f.schemas]}")

        # 2-b. save / load
        store.save()
        loaded = FAISSVectorStore.load(index_path)
        result_loaded = VectorRetriever.from_sources(
            catalog=CATALOG,
            embedding=embedding,
            vectorstore=loaded,
        )("주문 건수")
        assert len(result_loaded.schemas) > 0
        print(f"   save/load schemas: {[s['name'] for s in result_loaded.schemas]}")

        # 2-c. from_chunks (명시적 파이프라인)
        chunks = (
            CatalogChunker().split(CATALOG) +
            RecursiveCharacterChunker().split(DOCS)
        )
        store2 = FAISSVectorStore()
        retriever_fc = VectorRetriever.from_chunks(
            chunks, embedding=embedding, vectorstore=store2
        )
        result_fc = retriever_fc("매출 정의")
        assert len(result_fc.context) > 0
        print(f"   from_chunks context: {result_fc.context[0][:30]}...")

        # 2-d. 예외 처리
        try:
            FAISSVectorStore().save()
            assert False, "ValueError 미발생"
        except ValueError:
            pass

        try:
            FAISSVectorStore.load("no_such_file.faiss")
            assert False, "FileNotFoundError 미발생"
        except FileNotFoundError:
            pass

    print("   ✓ FAISSVectorStore 정상")

except ImportError:
    print("   ⚠ faiss 미설치 — 건너뜀")


# ── 3. PGVectorStore ───────────────────────────────────────────────────────────

print("\n3. PGVectorStore")

PG_URL = os.getenv("TEST_POSTGRES_URL")
if not PG_URL:
    print("   ⚠ TEST_POSTGRES_URL 미설정 — 건너뜀")
    print("   실행하려면: TEST_POSTGRES_URL=postgresql://... python <script>.py")
else:
    try:
        from lang2sql.integrations.vectorstore import PGVectorStore
        from uuid import uuid4

        table = f"test_{uuid4().hex[:8]}"
        store_pg = PGVectorStore(connection=PG_URL, table_name=table)

        # 3-a. from_sources
        retriever_pg = VectorRetriever.from_sources(
            catalog=CATALOG,
            embedding=embedding,
            vectorstore=store_pg,
        )
        result_pg = retriever_pg("주문 건수")
        assert len(result_pg.schemas) > 0
        print(f"   from_sources schemas: {[s['name'] for s in result_pg.schemas]}")

        # 3-b. 멱등 재인덱싱
        retriever_pg2 = VectorRetriever.from_sources(
            catalog=CATALOG,
            embedding=embedding,
            vectorstore=store_pg,
        )
        result_pg2 = retriever_pg2("주문 건수")
        assert len(result_pg2.schemas) > 0
        print(f"   idempotent re-index: {[s['name'] for s in result_pg2.schemas]}")

        # 3-c. from_chunks
        chunks_pg = CatalogChunker().split(CATALOG) + RecursiveCharacterChunker().split(DOCS)
        store_pg2 = PGVectorStore(connection=PG_URL, table_name=f"test_{uuid4().hex[:8]}")
        retriever_pgc = VectorRetriever.from_chunks(
            chunks_pg, embedding=embedding, vectorstore=store_pg2
        )
        result_pgc = retriever_pgc("매출 정의")
        assert len(result_pgc.context) > 0
        print(f"   from_chunks context: {result_pgc.context[0][:30]}...")

        # 정리
        for s in [store_pg, store_pg2]:
            with s._conn.cursor() as cur:
                cur.execute(f"DROP TABLE IF EXISTS {s._table};")
            s._conn.commit()
            s._conn.close()

        print("   ✓ PGVectorStore 정상")

    except Exception as e:
        print(f"   ✗ PGVectorStore 오류: {e}")


# ── 요약 ──────────────────────────────────────────────────────────────────────

print("\n" + "=" * 50)
print("체크리스트 완료")
print("=" * 50)
```

---

## 참고: 파이프라인 전체 흐름

```
[CATALOG / DOCS]
      │
      ▼  chunker.split()
  CatalogChunker / RecursiveCharacterChunker / SemanticChunker
      │  list[IndexedChunk]
      ▼
  VectorRetriever.from_chunks(chunks, embedding=..., vectorstore=...)
      ├── embedding.embed_texts(texts)
      └── vectorstore.upsert(ids, vectors)
           ├── InMemoryVectorStore  ← 기본값 (메모리)
           ├── FAISSVectorStore     ← 로컬 파일 (.faiss + .meta)
           └── PGVectorStore        ← PostgreSQL (pgvector)
      │
      ▼  retriever(query)
  embedding.embed_query(query)
      └── vectorstore.search(vector, k)
           └── RetrievalResult
               ├── .schemas  — 관련 CatalogEntry (중복 제거)
               └── .context  — 관련 문서 텍스트
      │
      ▼
  SQLGenerator → LLM → SQL → SQLExecutor → 결과
```
