# 05. 고급 — 수동 조합, 커스텀 어댑터, 관측성

각 컴포넌트를 개별 제어하고, 임베딩·벡터스토어·청커를 교체하는 방법을 다룹니다.

---

## 1) 완전 수동 Advanced Flow

`Retriever → Generator → Executor`를 직접 조합합니다.
각 단계의 입출력이 코드에 보여 디버깅과 파라미터 튜닝이 쉽습니다.

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

catalog = [
    {
        "name": "orders",
        "description": "주문 정보",
        "columns": {
            "order_id":   "주문 고유 ID",
            "order_date": "주문 일시",
            "amount":     "결제 금액",
            "status":     "주문 상태",
        },
    }
]

# 1) 문서 로드 + split
docs            = DirectoryLoader("docs/business").load()
embedding       = OpenAIEmbedding(model="text-embedding-3-small")
catalog_chunks  = CatalogChunker().split(catalog)
doc_chunks      = RecursiveCharacterChunker(chunk_size=800, chunk_overlap=80).split(docs)

# 2) Retriever 구성
retriever = VectorRetriever.from_chunks(
    catalog_chunks + doc_chunks,
    embedding=embedding,
    top_n=5,
    score_threshold=0.2,
)

# 3) Generator / Executor 개별 구성
generator = SQLGenerator(
    llm=OpenAILLM(model="gpt-4o-mini"),
    db_dialect="sqlite",
)
executor = SQLExecutor(db=SQLAlchemyDB("sqlite:///sample.db"))

# 4) 수동 실행 — 각 단계 결과 직접 관측
query     = "지난달 순매출 합계"
retrieval = retriever.run(query)
sql       = generator.run(query, retrieval.schemas, context=retrieval.context)
rows      = executor.run(sql)

print("SQL:", sql)
print("결과:", rows)
```

---

## 2) 임베딩 교체

`EmbeddingPort`를 만족하는 구현체라면 무엇이든 연결할 수 있습니다.

### v2 내장 임베딩

```python
from lang2sql.integrations.embedding import (
    OpenAIEmbedding,
    AzureOpenAIEmbedding,
    GeminiEmbedding,
    BedrockEmbedding,
    OllamaEmbedding,
    HuggingFaceEmbedding,
)

embedding = OpenAIEmbedding(model="text-embedding-3-small")
```

### 커스텀 어댑터 예시 (SentenceTransformer)

```python
class SentenceTransformerEmbedding:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(model_name)

    def embed_query(self, text: str) -> list[float]:
        return self._model.encode([text], normalize_embeddings=True)[0].tolist()

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return self._model.encode(texts, normalize_embeddings=True).tolist()

# 파이프라인 코드는 동일
retriever = VectorRetriever.from_sources(
    catalog=catalog,
    embedding=SentenceTransformerEmbedding(),
)
```

---

## 3) 벡터스토어 교체

`VectorStorePort`의 `upsert()`와 `search()`만 구현하면 됩니다.

### 커스텀 어댑터 예시 (Chroma)

```python
class ChromaVectorStore:
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

retriever = VectorRetriever.from_sources(
    catalog=catalog,
    embedding=OpenAIEmbedding(),
    vectorstore=ChromaVectorStore("my_catalog"),
)
```

---

## 4) 청커 교체

### SemanticChunker (opt-in)

```python
from lang2sql import CatalogChunker, VectorRetriever
from lang2sql.integrations.chunking import SemanticChunker
from lang2sql.integrations.embedding import OpenAIEmbedding

embedding = OpenAIEmbedding(model="text-embedding-3-small")

# from_chunks 패턴
doc_chunks = SemanticChunker(
    embedding=embedding,
    breakpoint_threshold=0.3,
    min_chunk_size=100,
).split(docs)

retriever = VectorRetriever.from_chunks(
    CatalogChunker().split(catalog) + doc_chunks,
    embedding=embedding,
)

# from_sources 패턴: splitter 파라미터로 전달
retriever = VectorRetriever.from_sources(
    catalog=catalog,
    documents=docs,
    embedding=embedding,
    splitter=SemanticChunker(embedding=embedding),
)
```

### LangChain 청커 어댑터

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter
from lang2sql import IndexedChunk, TextDocument

class LangChainChunkerAdapter:
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

lc_chunker = LangChainChunkerAdapter(
    RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
)

retriever = VectorRetriever.from_sources(
    catalog=catalog,
    documents=docs,
    embedding=OpenAIEmbedding(),
    splitter=lc_chunker,
)
```

---

## 5) DataHub 카탈로그 로더

DataHub GMS 서버에서 테이블 메타데이터를 가져와 `CatalogEntry` 목록으로 변환합니다.
수동으로 카탈로그를 작성하지 않아도 DataHub에 등록된 스키마 정보를 바로 사용할 수 있습니다.

```bash
pip install acryl-datahub
```

```python
from lang2sql.integrations.catalog import DataHubCatalogLoader

loader = DataHubCatalogLoader(
    gms_server="http://localhost:8080",
    extra_headers={"Authorization": "Bearer <token>"},
)

# 전체 URN 조회
catalog = loader.load()

# 특정 URN만 조회
catalog = loader.load(urns=[
    "urn:li:dataset:(urn:li:dataPlatform:postgres,mydb.public.orders,PROD)",
    "urn:li:dataset:(urn:li:dataPlatform:postgres,mydb.public.customers,PROD)",
])

# 바로 파이프라인에 연결
from lang2sql import BaselineNL2SQL
from lang2sql.integrations.db import SQLAlchemyDB
from lang2sql.integrations.llm import OpenAILLM

pipeline = BaselineNL2SQL(
    catalog=catalog,
    llm=OpenAILLM(model="gpt-4o-mini"),
    db=SQLAlchemyDB("postgresql://user:pass@localhost:5432/mydb"),
    db_dialect="postgresql",
)
```

> `DataHubCatalogLoader`는 `CatalogLoaderPort`를 구현합니다.
> DataHub 없이도 `SQLAlchemyExplorer`로 DDL을 직접 조회하거나 CSV/수동 카탈로그를 사용할 수 있습니다.

---

## 6) Port 프로토콜 레퍼런스

커스텀 어댑터를 작성할 때 구현해야 하는 메서드 목록입니다.

| Port | 메서드 | 시그니처 | 용도 |
|------|--------|----------|------|
| `LLMPort` | `invoke` | `(messages: list[dict]) -> str` | LLM 백엔드 교체 |
| `DBPort` | `execute` | `(sql: str) -> list[dict]` | DB 백엔드 교체 |
| `EmbeddingPort` | `embed_query` | `(text: str) -> list[float]` | 단일 텍스트 임베딩 |
| | `embed_texts` | `(texts: list[str]) -> list[list[float]]` | 배치 임베딩 |
| `VectorStorePort` | `upsert` | `(ids: list[str], vectors: list[list[float]]) -> None` | 벡터 저장 |
| | `search` | `(vector: list[float], k: int) -> list[tuple[str, float]]` | 유사도 검색 (id, score) |
| `DocumentLoaderPort` | `load` | `() -> list[TextDocument]` | 문서 로드 |
| `DocumentChunkerPort` | `chunk` | `(doc: TextDocument) -> list[IndexedChunk]` | 문서 분할 |
| `CatalogLoaderPort` | `load` | `(urns: list[str] \| None) -> list[CatalogEntry]` | 외부 카탈로그 로드 |
| `DBExplorerPort` | `list_tables` | `() -> list[str]` | 테이블 목록 |
| | `get_ddl` | `(table: str) -> str` | DDL 조회 |
| | `sample_data` | `(table: str, limit: int) -> list[dict]` | 샘플 데이터 |
| | `execute_read_only` | `(sql: str) -> list[dict]` | 읽기 전용 쿼리 |

모든 Port는 `src/lang2sql/core/ports.py`에 `Protocol`로 정의되어 있습니다.
클래스 상속 없이 **메서드 시그니처만 맞추면** 어떤 객체든 연결할 수 있습니다 (structural subtyping).

---

## 7) Hook — 관측성과 디버깅

`MemoryHook`으로 컴포넌트 단위 실행 이벤트를 수집합니다.

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
    embedding=OpenAIEmbedding(model="text-embedding-3-small"),
    documents=docs,
    db_dialect="sqlite",
    hook=hook,
)

pipeline.run("지난달 순매출 합계")

for e in hook.snapshot():
    print(f"{e.component:30s}  {e.phase:5s}  {e.duration_ms:6.1f}ms  error={e.error}")
```

출력 예시:
```
HybridRetriever                start   0.0ms  error=None
HybridRetriever                end    12.3ms  error=None
SQLGenerator                   start   0.0ms  error=None
SQLGenerator                   end   890.1ms  error=None
SQLExecutor                    start   0.0ms  error=None
SQLExecutor                    end     1.2ms  error=None
```

운영 환경에서는 `duration_ms`로 병목을 파악하고 `error` 이벤트를 수집해 장애 패턴을 분석합니다.

---

## 8) Best Practices 체크리스트

### 카탈로그 작성

- `description`은 한 문장으로 테이블 용도를 명확히 기술
- `columns`는 비즈니스 용어와 컬럼명 매핑을 충실히 작성
- 관련 테이블 간 FK 관계를 컬럼 설명에 명시

### 검색 파라미터

- `top_n`: 3~8로 시작해 실험 (너무 많으면 LLM 프롬프트 비용 증가)
- `score_threshold`: 0.0으로 시작 후 관련 없는 테이블이 검색될 때 0.3~0.5로 상향
- `rrf_k` (HybridRetriever): 기본값 60, 검색 결과 순위 민감도 조정

### 청킹

- 기본은 `RecursiveCharacterChunker`
- 문서 품질이 중요하고 비용 허용 시 `SemanticChunker` 검토
- `chunk_overlap`은 반드시 `chunk_size`보다 작게 설정

### 플로우 선택

| 우선 순위 | 파이프라인 |
|---|---|
| 빠른 시작 | `BaselineNL2SQL` |
| 검색 품질 | `HybridNL2SQL` |
| 운영 환경 | `EnrichedNL2SQL` |
| 세밀한 제어 | 수동 컴포넌트 조합 |

---

## 9) 트러블슈팅

### `IntegrationMissingError: openai`

```bash
pip install openai
```

### `chunk_overlap must be less than chunk_size`

`RecursiveCharacterChunker`의 `chunk_overlap < chunk_size` 조건 위반.
파라미터를 수정하세요.

### VectorRetriever 결과가 비어 있음

1. `from_chunks()` 또는 `from_sources()`가 실제로 호출됐는지 확인
2. `len(retriever._registry) > 0` 확인
3. `score_threshold`를 `0.0`으로 낮춰서 테스트

### `retriever.add()` 타입 에러

`add()`는 `list[IndexedChunk]`만 받습니다. `TextDocument`를 직접 전달하면 오류가 발생합니다.

```python
# ❌ 동작 안 함
retriever.add(docs)

# ✅ 올바른 방법
retriever.add(RecursiveCharacterChunker().split(docs))
```

### `IntegrationMissingError: pymupdf` (PDFLoader)

```bash
pip install pymupdf
```

### `ContractError` (EnrichedNL2SQL)

`QuestionGate`가 SQL로 답할 수 없다고 판단한 경우입니다.
`gate_enabled=False`로 비활성화하거나 질문을 SQL 관련으로 구체화하세요.
