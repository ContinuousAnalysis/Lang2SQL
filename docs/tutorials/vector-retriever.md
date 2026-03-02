# VectorRetriever 튜토리얼 — 벡터 유사도 검색으로 NL2SQL 정확도 높이기

이 튜토리얼은 `VectorRetriever`를 처음 사용하는 분을 위한 단계별 가이드입니다.
`KeywordRetriever`(BM25 키워드 검색)와 다른 점, 설정 방법, 파이프라인에 연결하는 방법을 설명합니다.

---

## 목차

1. [KeywordRetriever vs VectorRetriever — 언제 무엇을 쓸까?](#1-keywordretriever-vs-vectorretriever--언제-무엇을-쓸까)
2. [설치 — 임베딩 패키지 추가하기](#2-설치--임베딩-패키지-추가하기)
3. [가장 빠른 시작 — from_sources()](#3-가장-빠른-시작--from_sources)
4. [비즈니스 문서를 컨텍스트로 추가하기](#4-비즈니스-문서를-컨텍스트로-추가하기)
5. [파이프라인에 연결하기](#5-파이프라인에-연결하기)
6. [인덱스 점진적으로 추가하기 — add()](#6-인덱스-점진적으로-추가하기--add)
7. [고급 — 명시적 파이프라인 (from_chunks)](#7-고급--명시적-파이프라인-from_chunks)
8. [고급 — 청커 교체하기](#8-고급--청커-교체하기)
9. [점수 임계값과 top_n 조정](#9-점수-임계값과-top_n-조정)
10. [전체 체크리스트 — API 키 없이 실행](#10-전체-체크리스트--api-키-없이-실행)

---

## 1. KeywordRetriever vs VectorRetriever — 언제 무엇을 쓸까?

| | `KeywordRetriever` | `VectorRetriever` |
|---|---|---|
| **검색 방식** | BM25 키워드 매칭 | 벡터 코사인 유사도 |
| **강점** | 빠름, 외부 의존성 없음 | 동의어·의미 유사 쿼리에 강함 |
| **약점** | 질문과 컬럼명이 다를 때 누락 | 임베딩 API 또는 모델 필요 |
| **적합한 상황** | 카탈로그 규모가 작고 컬럼명이 명확할 때 | 카탈로그가 크거나, 비즈니스 용어가 컬럼명과 다를 때 |
| **비즈니스 문서 지원** | 없음 | 있음 (`context` 필드로 LLM에 전달) |

> **판단 기준**: `"매출"` 이라고 물었을 때 `amount` 컬럼이 검색되지 않으면 VectorRetriever로 교체하세요.

---

## 2. 설치

```bash
pip install lang2sql
```

`openai`는 lang2sql의 기본 의존성에 포함되어 있어 별도 설치가 필요 없습니다.

> 임베딩 API 없이 테스트하고 싶다면 **섹션 10**의 `FakeEmbedding`을 먼저 실행해 보세요.

---

## 3. 가장 빠른 시작 — from_sources()

`VectorRetriever.from_sources()` 한 줄로 인덱스를 만들고 즉시 검색할 수 있습니다.

```python
from lang2sql import VectorRetriever, CatalogEntry
from lang2sql.integrations.embedding import OpenAIEmbedding

CATALOG: list[CatalogEntry] = [
    {
        "name": "orders",
        "description": "고객 주문 정보 테이블. 주문 건수, 매출, 날짜 조회에 사용.",
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
        "description": "고객 마스터 데이터. 고객 이름, 가입일, 등급 조회에 사용.",
        "columns": {
            "customer_id": "고객 고유 ID (PK)",
            "name":        "고객 이름",
            "grade":       "고객 등급: bronze / silver / gold",
        },
    },
]

retriever = VectorRetriever.from_sources(
    catalog=CATALOG,
    embedding=OpenAIEmbedding(),  # OPENAI_API_KEY 환경변수 필요
)

result = retriever("매출 상위 고객 목록")

print(result.schemas)
# [{'name': 'orders', ...}, {'name': 'customers', ...}]

print(result.context)
# [] — 문서를 추가하지 않았으므로 빈 리스트
```

`from_sources()`는 내부적으로 다음을 자동으로 처리합니다:
- `InMemoryVectorStore` 생성 (외부 DB 불필요)
- 카탈로그 청킹 → 임베딩 → 저장 (`from_chunks()` 내부 호출)
- 검색 준비 완료된 `VectorRetriever` 반환

---

## 4. 비즈니스 문서를 컨텍스트로 추가하기

"매출"의 정의, KPI 계산 방식 같은 비즈니스 규칙을 문서로 등록하면
LLM이 SQL 생성 시 해당 내용을 참고합니다.

```python
from lang2sql import TextDocument

DOCS: list[TextDocument] = [
    {
        "id":      "revenue_def",
        "title":   "매출 정의",
        "content": "매출은 반품을 제외한 순매출(net sales)을 기준으로 한다. "
                   "취소(cancelled) 상태의 주문은 매출에서 제외한다.",
        "source":  "docs/revenue_definition.md",
    },
    {
        "id":      "grade_policy",
        "title":   "고객 등급 정책",
        "content": "gold 등급: 최근 3개월 누적 구매액 50만원 이상. "
                   "silver 등급: 20만원 이상. bronze: 그 외.",
        "source":  "docs/customer_grade.md",
    },
]

retriever = VectorRetriever.from_sources(
    catalog=CATALOG,
    documents=DOCS,       # ← 문서 동시 인덱싱
    embedding=OpenAIEmbedding(),
)

result = retriever("이번 달 매출을 집계해줘")

print(result.schemas)   # 관련 테이블 목록
print(result.context)   # 관련 문서 텍스트 — LLM 프롬프트에 포함됨
# ['매출 정의: 매출은 반품을 제외한 순매출...']
```

> `result.context`의 내용은 `SQLGenerator`가 프롬프트에 "Business Context" 섹션으로 자동 삽입합니다.

---

## 5. 파이프라인에 연결하기

벡터 기반 검색을 사용하려면 `HybridNL2SQL`을 사용합니다.
(`BaselineNL2SQL`은 `KeywordRetriever`만 내부적으로 사용하며, retriever 주입 파라미터를 받지 않습니다.)

```python
from lang2sql import HybridNL2SQL
from lang2sql.integrations.llm import AnthropicLLM
from lang2sql.integrations.db import SQLAlchemyDB
from lang2sql.integrations.embedding import OpenAIEmbedding

pipeline = HybridNL2SQL(
    catalog=CATALOG,
    llm=AnthropicLLM(model="claude-sonnet-4-6"),
    db=SQLAlchemyDB("sqlite:///sample.db"),
    embedding=OpenAIEmbedding(),
    documents=DOCS,
    db_dialect="sqlite",
)

rows = pipeline.run("취소 제외한 이번 달 매출 합계")
print(rows)
```

또는 `VectorRetriever`를 직접 조합해 수동 파이프라인을 구성할 수 있습니다:

```python
from lang2sql import VectorRetriever, SQLGenerator, SQLExecutor
from lang2sql.integrations.embedding import OpenAIEmbedding
from lang2sql.integrations.llm import AnthropicLLM
from lang2sql.integrations.db import SQLAlchemyDB

retriever = VectorRetriever.from_sources(
    catalog=CATALOG, documents=DOCS, embedding=OpenAIEmbedding(),
)
generator = SQLGenerator(llm=AnthropicLLM(model="claude-sonnet-4-6"), db_dialect="sqlite")
executor = SQLExecutor(db=SQLAlchemyDB("sqlite:///sample.db"))

query = "취소 제외한 이번 달 매출 합계"
result = retriever(query)
sql = generator(query, result.schemas, context=result.context)
rows = executor(sql)
```

---

## 6. 인덱스 점진적으로 추가하기 — add()

파이프라인이 실행 중일 때 새 문서를 동적으로 추가할 수 있습니다.
기존 카탈로그 인덱스는 그대로 유지됩니다.

```python
retriever = VectorRetriever.from_sources(
    catalog=CATALOG,
    embedding=OpenAIEmbedding(),
)

# 나중에 문서가 생겼을 때 추가
NEW_DOCS: list[TextDocument] = [
    {
        "id":      "discount_policy",
        "title":   "할인 정책",
        "content": "VIP 고객(gold 등급)에게는 정가의 10% 할인을 적용한다.",
        "source":  "docs/discount.md",
    },
]

retriever.add(RecursiveCharacterChunker().split(NEW_DOCS))  # pre-split 후 전달

result = retriever("VIP 고객 할인 금액 계산")
print(result.context)
# ['할인 정책: VIP 고객(gold 등급)에게는...']
```

> **주의**: `add()`는 `list[IndexedChunk]`만 받습니다.
> `TextDocument`를 직접 전달하면 오류가 발생합니다.
>
> ```python
> # ❌ 동작 안 함
> retriever.add(NEW_DOCS)
>
> # ✅ 올바른 방법
> retriever.add(RecursiveCharacterChunker().split(NEW_DOCS))
> ```

---

## 7. 고급 — 명시적 파이프라인 (from_chunks)

영속 벡터스토어(FAISS, pgvector)를 사용하거나,
카탈로그와 문서를 따로 스케줄링하고 싶을 때 `from_chunks()`를 직접 사용합니다.

```python
from lang2sql import CatalogChunker, RecursiveCharacterChunker, VectorRetriever
from lang2sql.integrations.embedding import OpenAIEmbedding
from lang2sql.integrations.vectorstore import FAISSVectorStore

embedding = OpenAIEmbedding()

# (1) 청킹 — 각 소스를 명시적으로 split
catalog_chunks = CatalogChunker().split(CATALOG)
doc_chunks = RecursiveCharacterChunker(chunk_size=500).split(DOCS)
all_chunks = catalog_chunks + doc_chunks

# (2) 영속 벡터스토어 지정
store = FAISSVectorStore(index_path="./index/catalog.faiss")

# (3) Retriever 생성 (embed + store 자동)
retriever = VectorRetriever.from_chunks(
    all_chunks,
    embedding=embedding,
    vectorstore=store,
)
store.save()  # 디스크에 저장

result = retriever("매출 정의")
```

`from_sources()` 대비 직접 제어가 필요한 경우:
- 벡터 저장소를 외부 DB(FAISS 파일, pgvector)로 교체할 때
- 인덱스를 디스크에 저장하고 재사용할 때
- 카탈로그와 문서를 따로 스케줄링할 때
- 청킹 중간 결과를 검사하거나 필터링할 때

---

## 8. 고급 — 청커 교체하기

### 기본 청커 비교

| 청커 | 위치 | 특징 |
|------|------|------|
| `CatalogChunker` | `components/retrieval/chunker.py` | 테이블 헤더 + 컬럼 그룹으로 분할. 스키마 검색 전용. |
| `RecursiveCharacterChunker` | `components/retrieval/chunker.py` | 문단→줄→문장 순 재귀 분할. 외부 의존성 없음. |
| `SemanticChunker` | `integrations/chunking/semantic_.py` | 임베딩 기반 의미 단위 분할. 품질 우선 시 사용. |

### SemanticChunker 사용하기 (opt-in)

```bash
pip install sentence-transformers  # 또는 openai 패키지
```

```python
from lang2sql import VectorRetriever
from lang2sql.integrations.chunking import SemanticChunker
from lang2sql.integrations.embedding import OpenAIEmbedding

embedding = OpenAIEmbedding()

retriever = VectorRetriever.from_sources(
    catalog=CATALOG,
    documents=DOCS,
    embedding=embedding,
    splitter=SemanticChunker(embedding=embedding),  # ← 의미 기반 청킹
)
```

### LangChain 청커 어댑터 (외부 라이브러리 연결)

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter
from lang2sql import IndexedChunk, TextDocument

class LangChainChunkerAdapter:
    """LangChain 텍스트 스플리터를 lang2sql DocumentChunkerPort에 맞게 감쌉니다."""

    def __init__(self, splitter):
        self._splitter = splitter

    def chunk(self, doc: TextDocument) -> list[IndexedChunk]:
        texts = self._splitter.split_text(doc["content"])
        title = doc.get("title", "")
        return [
            IndexedChunk(
                chunk_id=f"{doc['id']}__{i}",
                text=f"{title}: {text}" if title else text,
                source_type="document",
                source_id=doc["id"],
                chunk_index=i,
                metadata={"title": title, "source": doc.get("source", "")},
            )
            for i, text in enumerate(texts)
        ]


lc_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)

retriever = VectorRetriever.from_sources(
    catalog=CATALOG,
    documents=DOCS,
    embedding=OpenAIEmbedding(),
    splitter=LangChainChunkerAdapter(lc_splitter),
)
```

---

## 9. 점수 임계값과 top_n 조정

```python
retriever = VectorRetriever.from_sources(
    catalog=CATALOG,
    embedding=OpenAIEmbedding(),
    top_n=3,              # 반환할 최대 스키마/문서 수 (기본값: 5)
    score_threshold=0.5,  # 유사도가 이 값보다 낮은 결과는 제외 (기본값: 0.0)
)
```

| 파라미터 | 기본값 | 설명 |
|----------|--------|------|
| `top_n` | 5 | 반환하는 스키마(schemas)와 문서(context) 각각의 최대 수 |
| `score_threshold` | 0.0 | 이 값 **이하**의 유사도 점수는 결과에서 제외. 낮은 관련성 결과를 걸러낼 때 사용 |

> 관련 없는 테이블이 자꾸 검색된다면 `score_threshold`를 0.3~0.5 사이로 높여보세요.

---

## 10. 전체 체크리스트 — API 키 없이 실행

아래 코드는 실제 임베딩 API 없이 `FakeEmbedding`으로 모든 기능을 확인합니다.

```python
"""
VectorRetriever 전체 체크리스트
API 키 없이 FakeEmbedding으로 실행 가능합니다.
"""

# ── 0. FakeEmbedding 정의 ─────────────────────────────────────────────────────

class FakeEmbedding:
    """테스트용 고정 벡터 임베딩. 실제 유사도 계산은 하지 않습니다."""
    def embed_query(self, text: str) -> list[float]:
        return [0.1, 0.2, 0.3, 0.4]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3, 0.4]] * len(texts)


# ── 1. 카탈로그와 문서 준비 ──────────────────────────────────────────────────

from lang2sql import CatalogEntry, TextDocument

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
        "id":      "revenue_def",
        "title":   "매출 정의",
        "content": "매출은 반품 제외 순매출이며 cancelled 주문은 제외한다.",
        "source":  "docs/revenue.md",
    },
]


# ── 2. from_sources() — 카탈로그만 ───────────────────────────────────────────

from lang2sql import VectorRetriever

retriever = VectorRetriever.from_sources(
    catalog=CATALOG,
    embedding=FakeEmbedding(),
)

result = retriever("주문 건수")
print("✓ from_sources() — 카탈로그만")
print(f"  schemas: {[s['name'] for s in result.schemas]}")
print(f"  context: {result.context}")
assert isinstance(result.schemas, list)
assert result.context == []


# ── 3. from_sources() — 문서 포함 ────────────────────────────────────────────

retriever2 = VectorRetriever.from_sources(
    catalog=CATALOG,
    documents=DOCS,
    embedding=FakeEmbedding(),
)

result2 = retriever2("매출 정의")
print("\n✓ from_sources() — 문서 포함")
print(f"  schemas: {[s['name'] for s in result2.schemas]}")
print(f"  context: {result2.context}")
assert len(result2.context) >= 1


# ── 4. add() — 점진적 인덱싱 ─────────────────────────────────────────────────

from lang2sql import RecursiveCharacterChunker

initial_count = len(retriever._registry)

NEW_DOC: list[TextDocument] = [
    {
        "id":      "grade_policy",
        "title":   "등급 정책",
        "content": "gold 등급은 최근 3개월 50만원 이상 구매 고객이다.",
        "source":  "docs/grade.md",
    },
]

retriever.add(RecursiveCharacterChunker().split(NEW_DOC))  # pre-split 필수

print("\n✓ add() — 점진적 인덱싱")
print(f"  registry 크기: {initial_count} → {len(retriever._registry)}")
assert len(retriever._registry) > initial_count


# ── 5. score_threshold 필터링 ─────────────────────────────────────────────────

from lang2sql import CatalogChunker
from lang2sql.integrations.vectorstore import InMemoryVectorStore

catalog_chunks = CatalogChunker().split(CATALOG)
strict_retriever = VectorRetriever.from_chunks(
    catalog_chunks,
    embedding=FakeEmbedding(),
    # FakeEmbedding은 항상 동일 벡터 반환 → 코사인 유사도 = 1.0
    # score_threshold=1.0 이면 1.0 <= 1.0 조건 충족 → 전부 필터링됨
    score_threshold=1.0,
)

result3 = strict_retriever("주문")
print("\n✓ score_threshold=1.0 — 결과 필터링")
print(f"  schemas: {result3.schemas}  (빈 리스트 예상)")
assert result3.schemas == []


# ── 6. from_chunks — 카탈로그 + 문서 병합 ────────────────────────────────────

catalog_chunks2 = CatalogChunker().split(CATALOG)
doc_chunks2 = RecursiveCharacterChunker().split(DOCS)
all_chunks2 = catalog_chunks2 + doc_chunks2

retriever3 = VectorRetriever.from_chunks(
    all_chunks2,
    embedding=FakeEmbedding(),
)

catalog_ids = {c["chunk_id"] for c in catalog_chunks2}
for chunk_id in catalog_ids:
    assert chunk_id in retriever3._registry, f"카탈로그 청크 '{chunk_id}' 유실!"

print("\n✓ from_chunks — 카탈로그 + 문서 병합 확인")
print(f"  카탈로그 청크 수: {len(catalog_ids)}  (모두 존재)")


# ── 7. public import 확인 ────────────────────────────────────────────────────

from lang2sql import (
    VectorRetriever,
    CatalogChunker,
    RecursiveCharacterChunker,
    DocumentChunkerPort,
    RetrievalResult,
    TextDocument,
    IndexedChunk,
    EmbeddingPort,
    VectorStorePort,
)
print("\n✓ 모든 VectorRetriever 관련 import 성공")

print("\n" + "=" * 50)
print("모든 체크리스트 통과! VectorRetriever 사용 준비 완료.")
print("=" * 50)
```

---

## 참고: 아키텍처 한눈에 보기

```
[CATALOG / DOCS]
      │
      ▼  chunker.split()
  CatalogChunker             — 테이블 헤더 + 컬럼 그룹 분할
  RecursiveCharacterChunker  — 문서 분할 (또는 SemanticChunker)
      │
      ▼  list[IndexedChunk]
  VectorRetriever.from_chunks() / from_sources()
      │  embed_texts()
      ▼
  EmbeddingPort              — OpenAIEmbedding 등 (6개)
      │  upsert()
      ▼
  VectorStorePort            — InMemoryVectorStore / FAISSVectorStore / PGVectorStore
      │
      ▼
  VectorRetriever.__call__(query)
  ├── embed_query(query)
  ├── vectorstore.search(vector, k)
  └── RetrievalResult
      ├── .schemas  — 관련 CatalogEntry 목록 (중복 제거됨)
      └── .context  — 관련 문서 텍스트 목록
          │
          ▼
      SQLGenerator  — "Business Context" 섹션으로 프롬프트에 포함
```

**확장 포인트:**

| 인터페이스 | 구현할 메서드 | 용도 |
|-----------|------------|------|
| `EmbeddingPort` | `embed_query()`, `embed_texts()` | 임베딩 백엔드 교체 |
| `VectorStorePort` | `search()`, `upsert()` | 벡터 저장소 교체 (FAISS, pgvector 등) |
| `DocumentChunkerPort` | `chunk(doc)` | 청킹 전략 교체 |
