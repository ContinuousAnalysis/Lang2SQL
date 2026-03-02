# 03. 벡터 검색 — 인덱싱과 VectorStore

카탈로그와 비즈니스 문서를 벡터로 인덱싱해 의미 기반 검색을 수행합니다.

---

## 사전 준비

```bash
export OPENAI_API_KEY="sk-..."
python scripts/setup_sample_db.py
python scripts/setup_sample_docs.py   # docs/business/ 샘플 문서 생성
```

---

## 1) from_sources() — 원터치 인덱싱

청킹·임베딩·저장을 한 번에 처리합니다.

```python
from lang2sql import VectorRetriever
from lang2sql.integrations.embedding import OpenAIEmbedding

catalog = [
    {
        "name": "orders",
        "description": "고객 주문 정보. 주문 건수·금액·날짜 조회에 사용.",
        "columns": {
            "order_id":   "주문 고유 ID",
            "amount":     "주문 금액",
            "order_date": "주문 일시",
            "status":     "주문 상태",
        },
    },
]

docs = [
    {
        "id":      "revenue_def",
        "title":   "매출 정의",
        "content": "매출은 반품을 제외한 순매출이다. cancelled 상태 주문은 제외한다.",
        "source":  "docs/business/revenue.md",
    },
]

retriever = VectorRetriever.from_sources(
    catalog=catalog,
    documents=docs,
    embedding=OpenAIEmbedding(model="text-embedding-3-small"),
    top_n=5,
)

result = retriever.run("지난달 순매출 기준 집계")
print("schemas:", [s["name"] for s in result.schemas])
print("context:", result.context)
```

`from_sources()` 내부 동작:
1. `CatalogChunker`로 catalog split
2. `RecursiveCharacterChunker`로 docs split
3. `from_chunks()`로 embed + store (기본: `InMemoryVectorStore`)

---

## 2) from_chunks() — 명시적 파이프라인

split 단계를 직접 제어하거나 영속 store(FAISS, pgvector)를 쓸 때 사용합니다.

```python
from lang2sql import CatalogChunker, DirectoryLoader, RecursiveCharacterChunker, VectorRetriever
from lang2sql.integrations.embedding import OpenAIEmbedding

# 1) 문서 로딩
docs = DirectoryLoader("docs/business").load()

# 2) 명시적 split
catalog_chunks = CatalogChunker().split(catalog)
doc_chunks     = RecursiveCharacterChunker(chunk_size=800, chunk_overlap=80).split(docs)

# 3) embed + store
retriever = VectorRetriever.from_chunks(
    catalog_chunks + doc_chunks,
    embedding=OpenAIEmbedding(model="text-embedding-3-small"),
    top_n=5,
)

result = retriever.run("순매출 집계 기준")
print("schemas:", [s["name"] for s in result.schemas])
print("context:", result.context)
```

증분 추가:

```python
new_docs = DirectoryLoader("docs/new").load()
retriever.add(RecursiveCharacterChunker().split(new_docs))  # pre-split 필수
```

---

## 3) 문서 로더

### MarkdownLoader / PlainTextLoader

```python
from lang2sql import MarkdownLoader, PlainTextLoader

md_docs  = MarkdownLoader().load("docs/business/revenue.md")
txt_docs = PlainTextLoader().load("docs/business/rules.txt")
```

### DirectoryLoader (권장)

```python
from lang2sql import DirectoryLoader

# 기본: .md → MarkdownLoader, .txt → PlainTextLoader
docs = DirectoryLoader("docs/business").load()
print(f"로드된 문서 수: {len(docs)}")
```

### PDFLoader (opt-in)

```bash
pip install pymupdf
```

```python
from lang2sql import DirectoryLoader, MarkdownLoader
from lang2sql.integrations.loaders import PDFLoader

docs = DirectoryLoader(
    "docs/",
    loaders={
        ".md":  MarkdownLoader(),
        ".pdf": PDFLoader(),
    },
).load()
```

PDFLoader는 페이지 단위로 `TextDocument`를 생성합니다:
- `id`: `"{filename}__p{page_number}"`
- `title`: `"{filename} page {page_number}"`

---

## 4) FAISSVectorStore — 로컬 파일 영속성

### 인덱싱 후 저장

```python
from lang2sql import CatalogChunker, VectorRetriever
from lang2sql.integrations.embedding import OpenAIEmbedding
from lang2sql.integrations.vectorstore import FAISSVectorStore

store = FAISSVectorStore(index_path="./index/catalog.faiss")

chunks = CatalogChunker().split(catalog)
retriever = VectorRetriever.from_chunks(
    chunks,
    embedding=OpenAIEmbedding(model="text-embedding-3-large"),
    vectorstore=store,
)

# 벡터 인덱스 + registry 파일로 저장
retriever.save("./index/catalog")
# → ./index/catalog.faiss
# → ./index/catalog.faiss.meta
# → ./index/catalog.registry
```

### 재시작 시 로드

```python
from lang2sql import VectorRetriever
from lang2sql.integrations.embedding import OpenAIEmbedding
from lang2sql.integrations.vectorstore import FAISSVectorStore

embedding = OpenAIEmbedding(model="text-embedding-3-large")
store     = FAISSVectorStore.load("./index/catalog.faiss")

retriever = VectorRetriever.load(
    "./index/catalog",
    vectorstore=store,
    embedding=embedding,
)

result = retriever.run("주문 건수 집계")
```

### CSV → FAISS 인덱스 일괄 생성

DataHub 없이 CSV로 카탈로그를 만들고 FAISS로 인덱싱합니다.

```python
import csv, os
from collections import defaultdict
from lang2sql import CatalogChunker, VectorRetriever
from lang2sql.integrations.embedding import OpenAIEmbedding
from lang2sql.integrations.vectorstore import FAISSVectorStore

CSV_PATH   = "./dev/table_catalog.csv"
OUTPUT_DIR = "./index"

tables: dict = defaultdict(lambda: {"desc": "", "columns": {}})
with open(CSV_PATH, newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        t = row["table_name"].strip()
        tables[t]["desc"] = row["table_description"].strip()
        tables[t]["columns"][row["column_name"].strip()] = row["column_description"].strip()

catalog = [
    {"name": t, "description": info["desc"], "columns": info["columns"]}
    for t, info in tables.items()
]

os.makedirs(OUTPUT_DIR, exist_ok=True)
store  = FAISSVectorStore(index_path=f"{OUTPUT_DIR}/catalog.faiss")
chunks = CatalogChunker().split(catalog)

retriever = VectorRetriever.from_chunks(
    chunks,
    embedding=OpenAIEmbedding(model="text-embedding-3-large"),
    vectorstore=store,
)
retriever.save(f"{OUTPUT_DIR}/catalog")
print(f"저장 완료: {OUTPUT_DIR}/catalog")
```

---

## 5) PGVectorStore — PostgreSQL 영속성

### Docker로 pgvector 실행

```bash
docker run -d \
  --name pgvector \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  pgvector/pgvector:pg16
```

### 사용법

```python
from lang2sql import CatalogChunker, VectorRetriever
from lang2sql.integrations.embedding import OpenAIEmbedding
from lang2sql.integrations.vectorstore import PGVectorStore

store = PGVectorStore(
    connection="postgresql://postgres:postgres@localhost:5432/postgres",
    table_name="lang2sql_vectors",   # 첫 upsert 시 자동 생성
)

chunks = CatalogChunker().split(catalog)
retriever = VectorRetriever.from_chunks(
    chunks,
    embedding=OpenAIEmbedding(model="text-embedding-3-large"),
    vectorstore=store,
)
# save() 없음 — upsert()마다 DB에 즉시 반영
# 동일 chunk_id 재실행 시 덮어씀 (ON CONFLICT DO UPDATE)
```

---

## 6) 백엔드 비교

| | `InMemoryVectorStore` | `FAISSVectorStore` | `PGVectorStore` |
|---|---|---|---|
| 영속성 | 없음 | 파일 | PostgreSQL |
| Upsert | true upsert | append-only | true upsert |
| 멀티 서버 | 불가 | 불가 | 가능 |
| 권장 규모 | < 50k chunks | < 500k chunks | 500k+ chunks |

`vectorstore=` 파라미터만 교체하면 나머지 코드는 동일합니다.

---

## 7) top_n / score_threshold 조정

```python
retriever = VectorRetriever.from_sources(
    catalog=catalog,
    embedding=OpenAIEmbedding(),
    top_n=3,              # 반환할 최대 스키마/문서 수 (기본값: 5)
    score_threshold=0.3,  # 이 점수 이하는 결과에서 제외 (기본값: 0.0)
)
```

관련 없는 테이블이 검색될 때 `score_threshold`를 0.3~0.5로 올려보세요.

---

## 다음 단계

BM25 + 벡터 하이브리드 검색 → [04-hybrid.md](./04-hybrid.md)
