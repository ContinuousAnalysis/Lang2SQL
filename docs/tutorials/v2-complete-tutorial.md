# lang2sql v2 Complete Tutorial

이 문서는 `src/lang2sql` 기반 v2만 대상으로 합니다.
아래 순서대로 따라가면 초급에서 고급까지 모든 지원 경로를 직접 테스트할 수 있습니다.

- 난이도 상승 순서: 스크롤할수록 어려워집니다.
- 코드 예제는 현재 레포 구현 기준으로 작성되었습니다.
- 범위 외 기능(예: v2 내장 FAISS/PGVector)은 "커스텀 어댑터" 방식으로만 설명합니다.

---

## 목차

1. 목표와 범위
1-1. Why lang2sql
2. 사전 준비
3. 설치
4. API 키 설정
5. 샘플 DB 준비
5-1. 샘플 문서 자동 생성
6. 가장 쉬운 로컬 스모크 테스트 (API 키 없이)
7. BaselineNL2SQL 기본 사용 (KeywordRetriever)
8. 실제 LLM 연결 (OpenAI / Anthropic)
9. VectorRetriever 기초 (빠른 시작)
10. 문서 파싱: MarkdownLoader / PlainTextLoader / DirectoryLoader / PDFLoader
11. 명시적 파이프라인: from_chunks() 패턴
12. 청킹 전략 교체: Recursive vs Semantic
13. HybridRetriever / HybridNL2SQL
14. 임베딩 교체 테스트 (v2 내장 + 사용자 구현)
15. 벡터 스토어 교체 테스트 (v2 내장 + 사용자 구현)
16. 완전 수동 Advanced Flow 조합
17. 관측성(Tracing)과 디버깅
18. Best Practices 체크리스트
19. 트러블슈팅

---

## 1) 목표와 범위

이 튜토리얼의 목표:

- v2 코어 사용법을 처음 설치부터 끝까지 실습
- 기본 플로우, 벡터 인덱싱, 문서 로딩, 하이브리드 검색까지 검증
- 고급 사용자용 확장 포인트(Embedding/VectorStore/Chunker)를 직접 갈아끼워 테스트

중요 범위:

- 이 문서에서 "v2 공식 내장"은 아래만 의미합니다.
  - Embedding: `OpenAIEmbedding`
  - Vector store: `InMemoryVectorStore`
- 그 외는 Protocol 기반 "사용자 구현 어댑터" 방식으로 테스트합니다.

---

## 1-1) Why lang2sql

다른 라이브러리와 비교했을 때, v2에서 강조하는 포인트는 아래입니다.

- **운영 친화 기본선**: `Retriever -> Generator -> Executor` 경로가 짧고 실패 지점이 명확합니다.
- **명시적 인덱싱 파이프라인**: `chunker.split(docs)` → `VectorRetriever.from_chunks(chunks)` 패턴으로 split/embed/store 각 단계가 코드에 보입니다.
- **확장 포인트 분리**: 코어는 Protocol 기반이라 임베딩/벡터스토어/청커를 교체해도 플로우 코드는 유지됩니다.
- **관측성 내장**: Hook 이벤트(`start/end/error`, duration)를 컴포넌트 단위로 수집할 수 있습니다.

주의:
- v2는 "모든 기능을 직접 구현한 거대 프레임워크"가 목적이 아닙니다.
- 코어 오케스트레이션과 운영 안정성에 집중하고, 고급 백엔드는 교체 가능한 어댑터로 다룹니다.

---

## 2) 사전 준비

권장 환경:

- Python 3.11+
- `uv` 또는 `pip`
- (선택) OpenAI API 키, Anthropic API 키

---

## 3) 설치

### 옵션 A: pip
```bash
pip install lang2sql
```

### 옵션 B: 소스 기준 개발 설치
```bash
uv venv --python 3.11
source .venv/bin/activate
uv pip install -e .
```

---

## 4) API 키 설정

OpenAI/Anthropic SDK는 환경변수를 기본으로 읽습니다.

```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
```

---

## 5) 샘플 DB 준비

튜토리얼 전체를 재현하려면 샘플 DB를 먼저 만듭니다.

```bash
python scripts/setup_sample_db.py
```

완료되면 프로젝트 루트에 `sample.db`가 생성됩니다.

---

## 5-1) 샘플 문서 자동 생성

문서 로더/청킹/벡터 인덱싱 실습용 파일을 자동으로 생성합니다.

```bash
python scripts/setup_sample_docs.py
```

생성 위치(기본):
- `docs/business/revenue.md`
- `docs/business/order_status_policy.md`
- `docs/business/rules.txt`

기존 파일이 있을 때 덮어쓰려면:

```bash
python scripts/setup_sample_docs.py --force
```

---

## 6) 가장 쉬운 로컬 스모크 테스트 (API 키 없이)

먼저 외부 의존 없이 파이프라인 구조가 동작하는지 확인합니다.

```python
from lang2sql import BaselineNL2SQL

# 1) LLM을 흉내 내는 테스트 더블
class FakeLLM:
    def invoke(self, messages):
        # SQLGenerator는 ```sql ... ``` 블록을 기대합니다.
        return "```sql\nSELECT 1 AS ok\n```"

# 2) DB를 흉내 내는 테스트 더블
class FakeDB:
    def execute(self, sql):
        # SQLExecutor가 실행한 SQL을 받아 고정 결과를 반환
        return [{"ok": 1, "sql_received": sql}]

catalog = [
    {
        "name": "orders",
        "description": "주문 테이블",
        "columns": {"order_id": "주문 ID", "amount": "주문 금액"},
    }
]

pipeline = BaselineNL2SQL(
    catalog=catalog,
    llm=FakeLLM(),  # 외부 API 없이 테스트
    db=FakeDB(),    # 실제 DB 없이 테스트
    db_dialect="sqlite",
)

rows = pipeline.run("주문 건수 알려줘")
print(rows)
```

이 단계의 목적:

- 설치/임포트 문제 없는지 확인
- `Retriever -> Generator -> Executor` 기본 경로 확인

---

## 7) BaselineNL2SQL 기본 사용 (KeywordRetriever)

이제 실제 DB에 연결합니다.

```python
from lang2sql import BaselineNL2SQL
from lang2sql.integrations.db import SQLAlchemyDB
from lang2sql.integrations.llm import OpenAILLM

catalog = [
    {
        "name": "orders",
        "description": "고객 주문 정보",
        "columns": {
            "order_id": "주문 고유 ID",
            "customer_id": "고객 ID",
            "order_date": "주문 일시",
            "amount": "주문 금액",
            "status": "주문 상태",
        },
    },
    {
        "name": "customers",
        "description": "고객 마스터",
        "columns": {
            "customer_id": "고객 ID",
            "name": "고객명",
            "grade": "고객 등급",
        },
    },
]

pipeline = BaselineNL2SQL(
    catalog=catalog,
    llm=OpenAILLM(model="gpt-4o-mini"),
    db=SQLAlchemyDB("sqlite:///sample.db"),
    db_dialect="sqlite",
)

rows = pipeline.run("지난달 주문 건수")
print(rows)
```

주의:

- 현재 `BaselineNL2SQL`은 키워드 기반 리트리버를 내부에서 사용합니다.
- 벡터 검색 기반 플로우는 아래 `HybridNL2SQL` 또는 수동 조합을 사용하세요.

---

## 8) 실제 LLM 연결 (OpenAI / Anthropic)

LLM 백엔드는 교체 가능합니다.

### OpenAI LLM
```python
from lang2sql.integrations.llm import OpenAILLM
llm = OpenAILLM(model="gpt-4o-mini")
```

### Anthropic LLM
```python
from lang2sql.integrations.llm import AnthropicLLM
llm = AnthropicLLM(model="claude-sonnet-4-6")
```

둘 다 `LLMPort.invoke(messages)` 계약을 따르므로 플로우 코드는 동일합니다.

---

## 9) VectorRetriever 기초

두 가지 생성 패턴을 제공합니다. 상황에 맞게 선택하세요.

### 9-1. from_sources() — 원터치 (빠른 시작)

`VectorRetriever.from_sources()`는 split/embed/store를 한 번에 처리합니다.

```python
from lang2sql import VectorRetriever
from lang2sql.integrations.embedding import OpenAIEmbedding

catalog = [
    {
        "name": "orders",
        "description": "주문 정보 테이블",
        "columns": {
            "order_id": "주문 ID",
            "amount": "주문 금액",
            "discount_amount": "할인 금액",
            "order_date": "주문 날짜",
        },
    }
]

docs = [
    {
        "id": "biz_rules",
        "title": "매출 정의",
        "content": "매출은 반품 제외 순매출이다. 할인 금액은 discount_amount 컬럼을 사용한다.",
        "source": "docs/biz_rules.md",
    }
]

retriever = VectorRetriever.from_sources(
    catalog=catalog,
    documents=docs,
    embedding=OpenAIEmbedding(model="text-embedding-3-small"),
    top_n=5,
    score_threshold=0.0,
)

result = retriever.run("지난달 할인 매출")
print("schemas:", [s["name"] for s in result.schemas])
print("context:", result.context)
```

내부에서 일어나는 일:
1. catalog/docs를 각각 `CatalogChunker`, `RecursiveCharacterChunker`로 split
2. `from_chunks()`를 호출해 embed + store
3. 검색 가능한 `VectorRetriever` 반환

### 9-2. from_chunks() — 명시적 파이프라인 (LangChain 스타일)

split 단계를 직접 제어하고 싶을 때 사용합니다.

```python
from lang2sql import CatalogChunker, RecursiveCharacterChunker, VectorRetriever
from lang2sql.integrations.embedding import OpenAIEmbedding

# split 단계가 코드에 보임
catalog_chunks = CatalogChunker().split(catalog)
doc_chunks = RecursiveCharacterChunker(chunk_size=800, chunk_overlap=80).split(docs)

# chunks를 자유롭게 조합
retriever = VectorRetriever.from_chunks(
    catalog_chunks + doc_chunks,
    embedding=OpenAIEmbedding(model="text-embedding-3-small"),
    top_n=5,
)

result = retriever.run("지난달 할인 매출")
print("schemas:", [s["name"] for s in result.schemas])
print("context:", result.context)
```

`from_chunks()`의 장점:
- catalog/doc 외의 소스도 `IndexedChunk`를 직접 생성해 자유롭게 합칠 수 있음
- 커스텀 chunker와 조합하기 쉬움
- 증분 추가도 동일 패턴: `retriever.add(chunker.split(new_docs))`

---

## 10) 문서 파싱: MarkdownLoader / PlainTextLoader / DirectoryLoader / PDFLoader

문서를 수동으로 리스트 작성하지 않고 파일에서 읽어올 수 있습니다.

### 10-1. MarkdownLoader
```python
from lang2sql import MarkdownLoader

docs = MarkdownLoader().load("docs/business/revenue.md")
print(docs[0]["id"], docs[0]["title"], docs[0]["source"])
```

### 10-2. PlainTextLoader
```python
from lang2sql import PlainTextLoader

docs = PlainTextLoader().load("docs/business/rules.txt")
print(docs[0]["id"], docs[0]["title"], docs[0]["source"])
```

### 10-3. DirectoryLoader (권장)
```python
from lang2sql import DirectoryLoader

# 기본 매핑:
# .md  -> MarkdownLoader
# .txt -> PlainTextLoader
docs = DirectoryLoader("docs/business").load()
print("loaded docs:", len(docs))
for d in docs[:3]:
    print(d["id"], d["source"])
```

### 10-4. 로더 결과를 벡터 인덱싱에 연결
```python
from lang2sql import VectorRetriever, DirectoryLoader
from lang2sql.integrations.embedding import OpenAIEmbedding

docs = DirectoryLoader("docs/business").load()

retriever = VectorRetriever.from_sources(
    catalog=catalog,
    documents=docs,
    embedding=OpenAIEmbedding(),
)
```

### 10-5. Loader → split → from_chunks 플로우를 코드로 명시

```python
from lang2sql import (
    CatalogChunker,
    DirectoryLoader,
    RecursiveCharacterChunker,
    VectorRetriever,
)
from lang2sql.integrations.embedding import OpenAIEmbedding

catalog = [
    {
        "name": "orders",
        "description": "주문 정보",
        "columns": {
            "order_id": "주문 ID",
            "order_date": "주문 일시",
            "amount": "결제 금액",
            "discount_amount": "할인 금액",
        },
    }
]

# 1) document loader
docs = DirectoryLoader("docs/business").load()

# 2) 각 소스를 명시적으로 split
catalog_chunks = CatalogChunker().split(catalog)
doc_chunks = RecursiveCharacterChunker(chunk_size=800, chunk_overlap=80).split(docs)

# 3) from_chunks: embed + store를 한 번에
retriever = VectorRetriever.from_chunks(
    catalog_chunks + doc_chunks,
    embedding=OpenAIEmbedding(model="text-embedding-3-small"),
    top_n=5,
)

result = retriever.run("지난달 순매출 계산 규칙")
print("total chunks:", len(catalog_chunks) + len(doc_chunks))
print("schemas:", [s["name"] for s in result.schemas])
print("context sample:", result.context[:2])
```

정리:
- `DirectoryLoader`가 `TextDocument`를 만든다.
- `chunker.split(docs)`가 `list[IndexedChunk]`를 반환한다.
- `from_chunks()`가 embed + upsert + registry를 처리한다.
- `VectorRetriever`는 쿼리 시 검색만 수행한다.

### 10-6. 완전 수동 플로우 (내부 구조 직접 확인)

`chunk → embed → vectorstore.upsert`를 눈으로 확인하려면 아래처럼 직접 실행하면 됩니다.

```python
from lang2sql import CatalogChunker, RecursiveCharacterChunker, VectorRetriever
from lang2sql.integrations.embedding import OpenAIEmbedding
from lang2sql.integrations.vectorstore import InMemoryVectorStore

# 1) chunk — .split() 배치 호출
catalog_chunks = CatalogChunker(max_columns_per_chunk=20).split(catalog)
doc_chunks = RecursiveCharacterChunker(chunk_size=800, chunk_overlap=80).split(docs)
chunks = catalog_chunks + doc_chunks

# 2) embed
embedding = OpenAIEmbedding(model="text-embedding-3-small")
texts = [c["text"] for c in chunks]
vectors = embedding.embed_texts(texts)

# 3) vector store 저장(upsert)
store = InMemoryVectorStore()
ids = [c["chunk_id"] for c in chunks]
store.upsert(ids, vectors)

# 4) registry 구성
registry = {c["chunk_id"]: c for c in chunks}

# 5) retrieval 검증
retriever = VectorRetriever(
    vectorstore=store,
    embedding=embedding,
    registry=registry,
    top_n=5,
)
result = retriever.run("지난달 순매출 계산 규칙")
print("schemas:", [s["name"] for s in result.schemas])
print("context:", result.context[:2])
```

### 10-7. PDFLoader — PDF 파일 인덱싱

PDF는 `integrations.loaders`에서 opt-in으로 제공합니다 (`pip install pymupdf` 필요).

```python
from lang2sql import CatalogChunker, DirectoryLoader, MarkdownLoader, VectorRetriever
from lang2sql.integrations.embedding import OpenAIEmbedding
from lang2sql.integrations.loaders import PDFLoader

# PDFLoader를 DirectoryLoader에 추가 등록
docs = DirectoryLoader(
    "docs/",
    loaders={
        ".md": MarkdownLoader(),
        ".pdf": PDFLoader(),
    },
).load()

# 이후 일반 from_chunks 패턴과 동일
from lang2sql import RecursiveCharacterChunker

chunks = (
    CatalogChunker().split(catalog) +
    RecursiveCharacterChunker().split(docs)
)
retriever = VectorRetriever.from_chunks(
    chunks,
    embedding=OpenAIEmbedding(model="text-embedding-3-small"),
)
```

PDFLoader는 페이지 단위로 `TextDocument`를 생성합니다:
- `id`: `"{filename}__p{page_number}"` (1-indexed)
- `title`: `"{filename} page {page_number}"`
- `content`: 해당 페이지 추출 텍스트

---

## 11) 명시적 파이프라인: from_chunks() 패턴

고급 사용자는 split/embed/store 각 단계를 코드에서 명시적으로 제어합니다.

### 11-1. 기본 from_chunks() 패턴

```python
from lang2sql import CatalogChunker, RecursiveCharacterChunker, VectorRetriever
from lang2sql.integrations.embedding import OpenAIEmbedding

# 1) 각 소스를 명시적으로 split
catalog_chunks = CatalogChunker().split(catalog)
doc_chunks = RecursiveCharacterChunker().split(docs)

# 2) from_chunks: embed + store + registry 자동 처리
retriever = VectorRetriever.from_chunks(
    catalog_chunks + doc_chunks,
    embedding=OpenAIEmbedding(model="text-embedding-3-small"),
    top_n=5,
)

result = retriever.run("할인 매출")
print(result.schemas)
print(result.context)
```

### 11-2. 커스텀 VectorStore와 함께 사용

```python
from lang2sql.integrations.vectorstore import InMemoryVectorStore

store = InMemoryVectorStore()

retriever = VectorRetriever.from_chunks(
    catalog_chunks + doc_chunks,
    embedding=OpenAIEmbedding(model="text-embedding-3-small"),
    vectorstore=store,   # 커스텀 store 주입
    top_n=5,
    score_threshold=0.2,
)
```

### 11-3. 증분 추가 (add)

`add()`는 pre-split된 `list[IndexedChunk]`만 받습니다. 추가 전 반드시 split이 필요합니다.

```python
# 카탈로그/문서 초기 인덱싱
retriever = VectorRetriever.from_chunks(
    CatalogChunker().split(catalog),
    embedding=OpenAIEmbedding(model="text-embedding-3-small"),
)

# 나중에 문서 증분 추가
new_docs = DirectoryLoader("docs/new").load()
retriever.add(RecursiveCharacterChunker().split(new_docs))

result = retriever.run("할인 매출")
print(result.schemas)
```

Best practice:

- `from_chunks()`는 embed + upsert를 내부에서 처리 — store/registry 직접 관리 불필요
- catalog와 doc chunks는 Python list `+` 로 자유롭게 합칠 수 있음
- `add()`에는 반드시 `chunker.split(docs)` 결과를 전달

---

## 12) 청킹 전략 교체: Recursive vs Semantic

### 12-1. 기본 청커 (RecursiveCharacterChunker)

`from_sources()` — 원터치 패턴에서는 `splitter` 파라미터로 전달합니다.

```python
from lang2sql import VectorRetriever, RecursiveCharacterChunker
from lang2sql.integrations.embedding import OpenAIEmbedding

chunker = RecursiveCharacterChunker(
    chunk_size=1000,
    chunk_overlap=100,  # 반드시 chunk_size보다 작아야 함
)

retriever = VectorRetriever.from_sources(
    catalog=catalog,
    documents=docs,
    embedding=OpenAIEmbedding(),
    splitter=chunker,   # document_chunker 대신 splitter
)
```

`from_chunks()` — 명시적 패턴에서는 `.split()`을 직접 호출합니다.

```python
doc_chunks = RecursiveCharacterChunker(chunk_size=1000, chunk_overlap=100).split(docs)
retriever = VectorRetriever.from_chunks(
    CatalogChunker().split(catalog) + doc_chunks,
    embedding=OpenAIEmbedding(),
)
```

### 12-2. 의미 기반 청커 (SemanticChunker, opt-in)

```python
from lang2sql import CatalogChunker, VectorRetriever
from lang2sql.integrations.chunking import SemanticChunker
from lang2sql.integrations.embedding import OpenAIEmbedding

embedding = OpenAIEmbedding(model="text-embedding-3-small")

semantic_chunker = SemanticChunker(
    embedding=embedding,          # 청킹 단계에서도 임베딩 호출됨
    breakpoint_threshold=0.3,
    min_chunk_size=100,
)

# from_chunks 패턴: 청커를 직접 split에 사용
doc_chunks = semantic_chunker.split(docs)
retriever = VectorRetriever.from_chunks(
    CatalogChunker().split(catalog) + doc_chunks,
    embedding=embedding,
)

# 또는 from_sources 패턴: splitter 파라미터로 전달
retriever = VectorRetriever.from_sources(
    catalog=catalog,
    documents=docs,
    embedding=embedding,
    splitter=semantic_chunker,
)
```

주의:

- SemanticChunker는 인덱싱 비용/시간이 증가합니다.
- sentence split은 punctuation/newline 기반이라 문서 형식에 따라 튜닝이 필요합니다.

---

## 13) HybridRetriever / HybridNL2SQL

`HybridRetriever`는 BM25 + Vector를 RRF로 합쳐 안정적인 검색 결과를 제공합니다.

### 13-1. Retriever 단독 사용
```python
from lang2sql import HybridRetriever
from lang2sql.integrations.embedding import OpenAIEmbedding

retriever = HybridRetriever(
    catalog=catalog,
    embedding=OpenAIEmbedding(),
    documents=docs,
    top_n=5,
    rrf_k=60,
    score_threshold=0.0,
)

result = retriever.run("지난달 할인 매출")
print("schemas:", [s["name"] for s in result.schemas])
print("context:", result.context)
```

### 13-2. Flow로 바로 사용 (추천)
```python
from lang2sql import HybridNL2SQL
from lang2sql.integrations.db import SQLAlchemyDB
from lang2sql.integrations.embedding import OpenAIEmbedding
from lang2sql.integrations.llm import OpenAILLM

pipeline = HybridNL2SQL(
    catalog=catalog,
    llm=OpenAILLM(model="gpt-4o-mini"),
    db=SQLAlchemyDB("sqlite:///sample.db"),
    embedding=OpenAIEmbedding(),
    documents=docs,
    db_dialect="sqlite",
    top_n=5,
)

rows = pipeline.run("지난달 할인 매출")
print(rows)
```

---

## 14) 임베딩 교체 테스트 (v2 내장 + 사용자 구현)

v2 내장 임베딩은 `OpenAIEmbedding` 1개입니다.
하지만 `EmbeddingPort`를 만족하는 클래스를 구현하면 다른 임베딩도 바로 테스트할 수 있습니다.

### 14-1. 내장 OpenAIEmbedding
```python
from lang2sql.integrations.embedding import OpenAIEmbedding
embedding = OpenAIEmbedding(model="text-embedding-3-small")
```

### 14-2. API 키 없이 테스트용 FakeEmbedding
```python
class FakeEmbedding:
    # 문자열 길이/토큰 카운트 기반 간단 임베딩 (테스트용)
    def _vec(self, text: str) -> list[float]:
        return [
            float(len(text)),
            float(text.count("매출")),
            float(text.count("주문")),
            float(text.count("고객")),
        ]

    def embed_query(self, text: str) -> list[float]:
        return self._vec(text)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]
```

### 14-3. 외부 임베딩 어댑터 예시 (선택)
```python
class SentenceTransformerEmbedding:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(model_name)

    def embed_query(self, text: str) -> list[float]:
        return self._model.encode([text], normalize_embeddings=True)[0].tolist()

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return self._model.encode(texts, normalize_embeddings=True).tolist()
```

---

## 15) 벡터 스토어 교체 테스트 (v2 내장 + 사용자 구현)

v2 내장 VectorStore는 `InMemoryVectorStore` 1개입니다.
하지만 `VectorStorePort`를 만족하면 어떤 백엔드든 연결할 수 있습니다.

### 15-1. 내장 InMemoryVectorStore
```python
from lang2sql.integrations.vectorstore import InMemoryVectorStore
store = InMemoryVectorStore()
```

### 15-2. 사용자 구현 VectorStore 어댑터 (테스트용)
아래 코드는 "교체가 실제로 가능한지"를 검증하기 위한 최소 구현입니다.

```python
class TinyVectorStore:
    """
    학습/테스트용 최소 VectorStore 구현.
    메모리에 id->vector를 저장하고 cosine brute-force 검색을 수행합니다.
    """

    def __init__(self):
        self._rows = {}

    def upsert(self, ids: list[str], vectors: list[list[float]]) -> None:
        for i, v in zip(ids, vectors):
            self._rows[i] = v

    def search(self, vector: list[float], k: int) -> list[tuple[str, float]]:
        import math

        def cosine(a, b):
            dot = sum(x * y for x, y in zip(a, b))
            na = math.sqrt(sum(x * x for x in a)) + 1e-8
            nb = math.sqrt(sum(y * y for y in b)) + 1e-8
            return dot / (na * nb)

        ranked = sorted(
            ((i, cosine(v, vector)) for i, v in self._rows.items()),
            key=lambda x: x[1],
            reverse=True,
        )
        return ranked[:k]
```

### 15-3. 같은 코드에서 store만 갈아끼우기
```python
from lang2sql import VectorRetriever

# A) 내장 store
store_a = InMemoryVectorStore()

# B) 사용자 구현 store
store_b = TinyVectorStore()

# 나머지 코드(from_chunks/VectorRetriever)는 동일
```

이게 의미하는 바:

- 검색 정책(lang2sql 코어)은 유지
- 저장소 구현체만 교체

---

## 16) 완전 수동 Advanced Flow 조합

아래는 고급 사용자가 실제로 많이 쓰는 패턴입니다.

```python
from lang2sql import (
    CatalogChunker,
    DirectoryLoader,
    RecursiveCharacterChunker,
    SQLExecutor,
    SQLGenerator,
    VectorRetriever,
)
from lang2sql.integrations.db import SQLAlchemyDB
from lang2sql.integrations.embedding import OpenAIEmbedding
from lang2sql.integrations.llm import OpenAILLM

# 1) 문서 로드
docs = DirectoryLoader("docs/business").load()

# 2) 명시적 파이프라인: split → from_chunks
embedding = OpenAIEmbedding(model="text-embedding-3-small")

chunks = (
    CatalogChunker().split(catalog) +
    RecursiveCharacterChunker().split(docs)
)

retriever = VectorRetriever.from_chunks(
    chunks,
    embedding=embedding,
    top_n=5,
    score_threshold=0.2,
)

# 3) 생성 / 실행 컴포넌트 개별 구성
generator = SQLGenerator(
    llm=OpenAILLM(model="gpt-4o-mini"),
    db_dialect="sqlite",
)
executor = SQLExecutor(db=SQLAlchemyDB("sqlite:///sample.db"))

# 4) 플로우 수동 실행
query = "지난달 할인 반영 순매출"
retrieval = retriever.run(query)
sql = generator.run(query, retrieval.schemas, context=retrieval.context)
rows = executor.run(sql)

print("SQL:", sql)
print("Rows:", rows)
```

이 패턴 장점:

- split 단계가 코드에 보여 청킹 파라미터 튜닝이 직관적
- 각 단계 결과를 모두 관측 가능
- 임계값/청킹/임베딩/저장소를 독립 튜닝 가능
- 실패 지점 분리 디버깅 쉬움

---

## 17) 관측성(Tracing)과 디버깅

`MemoryHook`으로 컴포넌트/플로우 이벤트를 추적할 수 있습니다.

```python
from lang2sql import HybridNL2SQL, MemoryHook
from lang2sql.integrations.db import SQLAlchemyDB
from lang2sql.integrations.embedding import OpenAIEmbedding
from lang2sql.integrations.llm import OpenAILLM

hook = MemoryHook()

pipeline = HybridNL2SQL(
    catalog=catalog,
    llm=OpenAILLM(model="gpt-4o-mini"),
    db=SQLAlchemyDB("sqlite:///sample.db"),
    embedding=OpenAIEmbedding(),
    documents=docs,
    db_dialect="sqlite",
    top_n=5,
    hook=hook,
)

pipeline.run("지난달 주문 건수")

for e in hook.snapshot():
    print(e.name, e.component, e.phase, e.duration_ms)
```

운영 관점 권장:

- `duration_ms`를 컴포넌트별로 기록해 병목 확인
- `error` 이벤트를 수집해 장애 패턴 분석

---

## 18) Best Practices 체크리스트

### 검색/인덱싱
- `catalog`는 최소 `name`, `description`, `columns`를 충실히 작성
- 문서는 한 파일에 너무 많은 주제를 넣지 말고 주제별 분리
- `top_n`은 3~8 범위에서 시작해 실험
- `score_threshold`는 0.0으로 시작 후 점진 상향

### 청킹
- 기본은 `RecursiveCharacterChunker`
- 문서 품질이 중요하고 비용 허용 시 `SemanticChunker` 검토
- `chunk_overlap`은 `chunk_size`보다 반드시 작게 설정

### 플로우 선택
- 빠른 시작: `BaselineNL2SQL`
- 검색 품질 우선: `HybridNL2SQL`
- 완전 제어: 수동 컴포넌트 조합

### 운영
- Hook 이벤트를 저장하고 p95 지표를 모니터링
- 회귀 테스트를 정기 실행

```bash
pytest tests/test_components_vector_retriever.py -q
pytest tests/test_components_hybrid_retriever.py -q
pytest tests/test_components_loaders.py -q
```

---

## 19) 트러블슈팅

### Q1. `IntegrationMissingError: openai`
- 원인: `openai` 패키지 미설치
- 해결:
```bash
pip install openai
```

### Q2. `chunk_overlap must be less than chunk_size`
- 원인: `RecursiveCharacterChunker` 파라미터 설정 오류
- 해결: `chunk_overlap < chunk_size`로 수정

### Q3. VectorRetriever 결과가 비어 있음
- 확인 순서:
1. `from_chunks(chunks, ...)` 또는 `from_sources(catalog=..., ...)` 가 실제로 호출되었는지
2. `len(retriever._registry) > 0`인지 확인
3. `score_threshold`가 너무 높지 않은지 (0.0으로 낮춰서 테스트)

### Q4. `retriever.add()` 호출 시 타입 에러
- 원인: `add()`는 `list[IndexedChunk]`만 받습니다. `TextDocument`를 직접 전달하면 에러가 발생합니다.
- 해결: 추가 전 반드시 `chunker.split(docs)`로 변환하세요:
```python
# ❌ 동작 안 함
retriever.add(docs)

# ✅ 올바른 방법
retriever.add(RecursiveCharacterChunker().split(docs))
```

### Q5. `IntegrationMissingError: pymupdf`
- 원인: `PDFLoader` 사용 시 `pymupdf` 미설치
- 해결:
```bash
pip install pymupdf
```

---

## 마무리

이 문서의 순서대로 진행하면 아래 모든 경로를 실제로 검증할 수 있습니다.

- Baseline keyword 플로우
- VectorRetriever + 문서 인덱싱
- HybridRetriever / HybridNL2SQL
- Loader/Chunker/Embedding/VectorStore 교체
- 수동 Advanced Flow 및 tracing

빠르게 시작하려면:

1. 6단계(로컬 스모크 테스트)
2. 7단계(Baseline)
3. 13단계(HybridNL2SQL)

고급 운영 튜닝까지 가려면:

4. 11~16단계(from_chunks/어댑터/수동조합)까지 진행하세요.
