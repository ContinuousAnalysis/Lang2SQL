# lang2sql v2 Usage Guide

이 문서는 `src/lang2sql` 기준의 새로운 v2 API만 다룹니다.
기존 `engine/`, `interface/`, `utils/llm/` 경로는 범위에서 제외합니다.

자세한 단계별 실습은 [v2-complete-tutorial.md](./v2-complete-tutorial.md) 를 참고하세요.

## 0) Why lang2sql

- **운영 친화적인 기본 경로**: `Retriever -> Generator -> Executor`가 단순하고 디버깅 포인트가 명확합니다.
- **명시적 인덱싱 파이프라인**: `chunker.split(docs)` → `VectorRetriever.from_chunks(chunks)` 패턴으로 split/embed/store 각 단계가 코드에 보입니다.
- **프레임워크 락인 최소화**: 코어가 Protocol(`EmbeddingPort`, `VectorStorePort`, `DocumentChunkerPort`) 기반이라 구현체를 교체하기 쉽습니다.
- **관측성 내장**: Hook(`TraceHook`, `MemoryHook`)으로 컴포넌트 단위 실행 이벤트를 바로 수집할 수 있습니다.

## 0-1) 튜토리얼 데이터 자동 준비

```bash
python scripts/setup_sample_db.py
python scripts/setup_sample_docs.py
```

문서 생성 후 `docs/business` 아래 파일을 로더 예제에서 그대로 사용합니다.

## 1) v2에서 실제로 지원되는 기능

### Flows
- `BaselineNL2SQL`: BM25 `KeywordRetriever` 기반 기본 파이프라인
- `HybridNL2SQL`: BM25 + Vector `HybridRetriever` 기반 파이프라인

### Retrievers
- `KeywordRetriever`
- `VectorRetriever`
- `HybridRetriever`

### Vector / Embedding (v2 내장)
- Embedding: `OpenAIEmbedding` (내장 1개)
- Vector store: `InMemoryVectorStore` (내장 1개)

### Chunking / Loading
- Chunkers: `CatalogChunker`, `RecursiveCharacterChunker`, `SemanticChunker`
  - 모두 `.split(list)` 메서드 제공 — LangChain 스타일 batch 입력/출력
- Loaders: `MarkdownLoader`, `PlainTextLoader`, `DirectoryLoader`
  - `PDFLoader` (optional, `pip install pymupdf`)

### Extensibility (Protocol)
- `EmbeddingPort`, `VectorStorePort`, `DocumentChunkerPort`, `DocumentLoaderPort`
- 즉, 내장 구현 외에도 사용자 어댑터를 연결할 수 있습니다.

## 2) 빠른 선택 가이드

### 가장 쉬운 시작
- 목적: 설치 후 바로 NL2SQL 확인
- 선택: `BaselineNL2SQL`
- 특징: 벡터 인덱싱 없이 즉시 사용

### 검색 품질을 빠르게 올리고 싶을 때
- 목적: 키워드 매칭 한계를 보완
- 선택: `HybridNL2SQL` + `OpenAIEmbedding`
- 특징: BM25 + Vector RRF 결합으로 안정적인 검색 품질

### 고급 제어가 필요할 때
- 목적: 청킹/임베딩/인덱싱/검색 파이프라인 세밀 제어
- 선택: `chunker.split()` + `VectorRetriever.from_chunks()` + 수동 컴포넌트 조합
- 특징: 증분 인덱싱, 커스텀 Chunker/VectorStore/Embedding 연동 가능

## 3) 최소 예제

### A. BaselineNL2SQL (키워드 기반)
```python
from lang2sql import BaselineNL2SQL
from lang2sql.integrations.db import SQLAlchemyDB
from lang2sql.integrations.llm import OpenAILLM

catalog = [
    {
        "name": "orders",
        "description": "order table",
        "columns": {"order_id": "pk", "amount": "order amount"},
    }
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

### B. HybridNL2SQL (키워드 + 벡터)
```python
from lang2sql import HybridNL2SQL
from lang2sql.integrations.db import SQLAlchemyDB
from lang2sql.integrations.embedding import OpenAIEmbedding
from lang2sql.integrations.llm import OpenAILLM

catalog = [
    {
        "name": "orders",
        "description": "order table",
        "columns": {"order_id": "pk", "amount": "order amount"},
    }
]

docs = [
    {
        "id": "biz_rules",
        "title": "매출 정의",
        "content": "매출은 반품 제외 순매출이다.",
        "source": "docs/biz_rules.md",
    }
]

pipeline = HybridNL2SQL(
    catalog=catalog,
    llm=OpenAILLM(model="gpt-4o-mini"),
    db=SQLAlchemyDB("sqlite:///sample.db"),
    embedding=OpenAIEmbedding(model="text-embedding-3-small"),
    documents=docs,
    db_dialect="sqlite",
    top_n=5,
)

rows = pipeline.run("지난달 순매출")
print(rows)
```

### C. 명시적 파이프라인: split → from_chunks (LangChain 스타일)
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
        "description": "order table",
        "columns": {"order_id": "pk", "amount": "order amount"},
    }
]

# 1) 문서 로딩
docs = DirectoryLoader("docs/business").load()

# 2) 각 소스를 명시적으로 split
catalog_chunks = CatalogChunker().split(catalog)
doc_chunks = RecursiveCharacterChunker(chunk_size=800, chunk_overlap=80).split(docs)

# 3) chunks를 합쳐서 retriever 생성 (embed + store 자동)
retriever = VectorRetriever.from_chunks(
    catalog_chunks + doc_chunks,
    embedding=OpenAIEmbedding(model="text-embedding-3-small"),
    top_n=5,
)

result = retriever.run("순매출 계산 기준")
print("schemas:", [s["name"] for s in result.schemas])
print("context:", result.context[:2])
```

명시적 플로우의 장점:

1. split 단계가 코드에 보임 — `chunker.split(docs)`가 명시적
2. catalog chunks + doc chunks를 Python list로 자유롭게 조합 가능
3. `registry = {}` 같은 내부 상태를 사용자가 직접 관리할 필요 없음

증분 추가 시에는 chunks를 미리 split한 뒤 전달합니다:

```python
new_docs = DirectoryLoader("docs/new").load()
retriever.add(RecursiveCharacterChunker().split(new_docs))
```

### D. DirectoryLoader → HybridNL2SQL 직결

문서를 로드한 뒤 바로 HybridNL2SQL에 전달하는 가장 간결한 패턴입니다.

```python
from lang2sql import DirectoryLoader, HybridNL2SQL
from lang2sql.integrations.db import SQLAlchemyDB
from lang2sql.integrations.embedding import OpenAIEmbedding
from lang2sql.integrations.llm import OpenAILLM

docs = DirectoryLoader("docs/business").load()

pipeline = HybridNL2SQL(
    catalog=catalog,
    llm=OpenAILLM(model="gpt-4o-mini"),
    db=SQLAlchemyDB("sqlite:///sample.db"),
    embedding=OpenAIEmbedding(model="text-embedding-3-small"),
    documents=docs,
    db_dialect="sqlite",
)

rows = pipeline.run("지난달 순매출")
print(rows)
```

### E. PDFLoader — PDF 파일 인덱싱

PDF 파일은 `PDFLoader`로 로드합니다 (`pip install pymupdf` 필요).

```python
from lang2sql import DirectoryLoader, MarkdownLoader, VectorRetriever
from lang2sql.integrations.embedding import OpenAIEmbedding
from lang2sql.integrations.loaders import PDFLoader

# PDFLoader를 DirectoryLoader에 등록
docs = DirectoryLoader(
    "docs/",
    loaders={
        ".md": MarkdownLoader(),
        ".pdf": PDFLoader(),
    },
).load()

# 이후 from_chunks 패턴으로 인덱싱
from lang2sql import CatalogChunker, RecursiveCharacterChunker

chunks = (
    CatalogChunker().split(catalog) +
    RecursiveCharacterChunker().split(docs)
)
retriever = VectorRetriever.from_chunks(
    chunks,
    embedding=OpenAIEmbedding(model="text-embedding-3-small"),
)
```

PDF는 페이지 단위로 `TextDocument`를 생성합니다:
- `id`: `"{filename}__p{page_number}"`
- `title`: `"{filename} page {page_number}"`

## 4) 중요한 현재 제약

- v2 내장 VectorStore는 현재 `InMemoryVectorStore`만 공식 제공됩니다.
- `BaselineNL2SQL`은 현재 `retriever` 주입 파라미터를 받지 않습니다.
  - 벡터 기반 파이프라인은 `HybridNL2SQL` 또는 수동 조합을 사용하세요.
- `VectorRetriever` 결과의 `context`는 현재 `list[str]`입니다.
  - 문서 출처 구조화가 필요하면 `metadata`를 별도 조회하거나 커스텀 래퍼를 두세요.
- `retriever.add()`는 **`list[IndexedChunk]`만 받습니다** — `TextDocument` 직접 전달 불가.
  - 추가 전 반드시 `chunker.split(docs)`로 split한 결과를 전달하세요:
    ```python
    # ❌ 동작 안 함
    retriever.add(docs)

    # ✅ 올바른 방법
    retriever.add(RecursiveCharacterChunker().split(docs))
    ```

## 5) 추천 실습 순서

1. [v2-complete-tutorial.md](./v2-complete-tutorial.md) 1~4단계로 로컬 스모크 테스트
2. 동일 문서 5~8단계로 실제 DB/LLM 연결
3. 동일 문서 9~13단계로 벡터 인덱싱/문서 파싱/청킹 튜닝
4. 동일 문서 14~18단계로 고급 조합과 커스텀 어댑터 테스트
