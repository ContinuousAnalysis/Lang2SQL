# Production Test Guide — v2 Migration

이 문서는 v2 마이그레이션에서 수행된 모든 변경 사항을 **실제 API 키와 실제 DB**를 사용해 프로덕션 수준에서 검증하는 가이드입니다.

---

## 전제 조건

```bash
# 의존성 설치
uv sync --group dev

# .env 설정 (아래 각 섹션에서 사용할 프로바이더 항목을 활성화)
cp .env.example .env
```

모든 Python 스니펫은 프로젝트 루트에서 실행합니다:

```bash
cd /path/to/lang2sql
```

---

## 1. LLM 통합 — 7개 프로바이더

각 프로바이더는 `.env`에서 해당 항목을 설정하고 독립적으로 검증합니다.

### 1-A. Anthropic

```
# .env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_LLM_MODEL=claude-sonnet-4-6
```

```python
from lang2sql.integrations.llm.anthropic_ import AnthropicLLM
import os

llm = AnthropicLLM(model="claude-sonnet-4-6", api_key=os.getenv("ANTHROPIC_API_KEY"))
resp = llm.invoke([{"role": "user", "content": "Respond with just 'OK'"}])
assert resp.strip() == "OK", f"Unexpected: {resp}"
print("Anthropic LLM ✓")
```

**확인 포인트**
- `invoke()` 반환값이 `str` 타입
- system 메시지가 `role: system`으로 분리되어 Anthropic Messages API에 전달됨

---

### 1-B. OpenAI

```
# .env
LLM_PROVIDER=openai
OPEN_AI_KEY=sk-proj-...
OPEN_AI_LLM_MODEL=gpt-4o
```

```python
from lang2sql.integrations.llm.openai_ import OpenAILLM
import os

llm = OpenAILLM(model="gpt-4o", api_key=os.getenv("OPEN_AI_KEY"))
resp = llm.invoke([{"role": "user", "content": "Respond with just 'OK'"}])
assert isinstance(resp, str) and len(resp) > 0
print("OpenAI LLM ✓")
```

---

### 1-C. Azure OpenAI

```
# .env
LLM_PROVIDER=azure
AZURE_OPENAI_LLM_ENDPOINT=https://RESOURCE.openai.azure.com/
AZURE_OPENAI_LLM_KEY=...
AZURE_OPENAI_LLM_MODEL=gpt4o          # Azure deployment name
AZURE_OPENAI_LLM_API_VERSION=2024-07-01-preview
```

```python
from lang2sql.integrations.llm.azure_ import AzureOpenAILLM
import os

llm = AzureOpenAILLM(
    azure_deployment=os.environ["AZURE_OPENAI_LLM_MODEL"],
    azure_endpoint=os.environ["AZURE_OPENAI_LLM_ENDPOINT"],
    api_version=os.getenv("AZURE_OPENAI_LLM_API_VERSION", "2024-07-01-preview"),
    api_key=os.getenv("AZURE_OPENAI_LLM_KEY"),
)
resp = llm.invoke([{"role": "user", "content": "Respond with just 'OK'"}])
assert isinstance(resp, str) and len(resp) > 0
print("Azure OpenAI LLM ✓")
```

---

### 1-D. Google Gemini

```
# .env
LLM_PROVIDER=gemini
GEMINI_API_KEY=AIza...
GEMINI_LLM_MODEL=gemini-2.0-flash-lite
```

```python
from lang2sql.integrations.llm.gemini_ import GeminiLLM
import os

llm = GeminiLLM(model="gemini-2.0-flash-lite", api_key=os.getenv("GEMINI_API_KEY"))
resp = llm.invoke([{"role": "user", "content": "Respond with just 'OK'"}])
assert isinstance(resp, str) and len(resp) > 0
print("Gemini LLM ✓")
```

---

### 1-E. AWS Bedrock

```
# .env
LLM_PROVIDER=bedrock
AWS_BEDROCK_LLM_ACCESS_KEY_ID=AKI...
AWS_BEDROCK_LLM_SECRET_ACCESS_KEY=...
AWS_BEDROCK_LLM_REGION=us-east-1
AWS_BEDROCK_LLM_MODEL=anthropic.claude-3-5-sonnet-20241022-v2:0
```

```python
from lang2sql.integrations.llm.bedrock_ import BedrockLLM
import os

llm = BedrockLLM(
    model=os.environ["AWS_BEDROCK_LLM_MODEL"],
    aws_access_key_id=os.getenv("AWS_BEDROCK_LLM_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_BEDROCK_LLM_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_BEDROCK_LLM_REGION", "us-east-1"),
)
resp = llm.invoke([{"role": "user", "content": "Respond with just 'OK'"}])
assert isinstance(resp, str) and len(resp) > 0
print("Bedrock LLM ✓")
```

**확인 포인트**: Bedrock Converse API 포맷 — `role: system`이 `system` 블록으로 분리되는지 확인

```python
# system 메시지 분리 확인
resp = llm.invoke([
    {"role": "system", "content": "Always respond in one word."},
    {"role": "user", "content": "Say hello"},
])
assert len(resp.split()) <= 3, f"System prompt not applied: {resp}"
print("Bedrock system message separation ✓")
```

---

### 1-F. Ollama (로컬)

```
# Ollama 서버 실행 필요
# brew install ollama && ollama serve
# ollama pull llama3.2

# .env
LLM_PROVIDER=ollama
OLLAMA_LLM_BASE_URL=http://localhost:11434
OLLAMA_LLM_MODEL=llama3.2
```

```python
from lang2sql.integrations.llm.ollama_ import OllamaLLM
import os

llm = OllamaLLM(
    model=os.environ["OLLAMA_LLM_MODEL"],
    base_url=os.getenv("OLLAMA_LLM_BASE_URL", "http://localhost:11434"),
)
resp = llm.invoke([{"role": "user", "content": "Say hello in one word"}])
assert isinstance(resp, str) and len(resp) > 0
print("Ollama LLM ✓")
```

---

### 1-G. HuggingFace Inference API

```
# .env
LLM_PROVIDER=huggingface
HUGGING_FACE_LLM_REPO_ID=mistralai/Mistral-7B-Instruct-v0.3
HUGGING_FACE_LLM_API_TOKEN=hf_...
# HUGGING_FACE_LLM_ENDPOINT=https://... (Dedicated Endpoint 사용 시)
```

```python
from lang2sql.integrations.llm.huggingface_ import HuggingFaceLLM
import os

llm = HuggingFaceLLM(
    repo_id=os.getenv("HUGGING_FACE_LLM_REPO_ID"),
    api_token=os.getenv("HUGGING_FACE_LLM_API_TOKEN"),
)
resp = llm.invoke([{"role": "user", "content": "Say hello"}])
assert isinstance(resp, str) and len(resp) > 0
print("HuggingFace LLM ✓")
```

---

## 2. Embedding 통합 — 6개 프로바이더

### 2-A. OpenAI Embedding

```python
from lang2sql.integrations.embedding.openai_ import OpenAIEmbedding
import os

emb = OpenAIEmbedding(
    model="text-embedding-3-small",
    api_key=os.getenv("OPEN_AI_KEY"),
)
vec = emb.embed_query("주문 테이블의 주문 ID")
assert isinstance(vec, list) and len(vec) == 1536
print(f"OpenAI Embedding ✓ (dim={len(vec)})")

vecs = emb.embed_texts(["orders", "customers"])
assert len(vecs) == 2 and len(vecs[0]) == 1536
print("OpenAI batch embed ✓")
```

---

### 2-B. Azure OpenAI Embedding

```
# .env
EMBEDDING_PROVIDER=azure
AZURE_OPENAI_EMBEDDING_ENDPOINT=https://RESOURCE.openai.azure.com/
AZURE_OPENAI_EMBEDDING_KEY=...
AZURE_OPENAI_EMBEDDING_MODEL=textembeddingada002
AZURE_OPENAI_EMBEDDING_API_VERSION=2023-09-15-preview
```

```python
from lang2sql.integrations.embedding.azure_ import AzureOpenAIEmbedding
import os

emb = AzureOpenAIEmbedding(
    azure_deployment=os.environ["AZURE_OPENAI_EMBEDDING_MODEL"],
    azure_endpoint=os.environ["AZURE_OPENAI_EMBEDDING_ENDPOINT"],
    api_version=os.getenv("AZURE_OPENAI_EMBEDDING_API_VERSION"),
    api_key=os.getenv("AZURE_OPENAI_EMBEDDING_KEY"),
)
vec = emb.embed_query("주문 데이터")
assert isinstance(vec, list) and len(vec) > 0
print(f"Azure Embedding ✓ (dim={len(vec)})")
```

---

### 2-C. Ollama Embedding

```
# .env
EMBEDDING_PROVIDER=ollama
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_EMBEDDING_BASE_URL=http://localhost:11434
```

```python
# ollama pull nomic-embed-text 먼저 실행 필요
from lang2sql.integrations.embedding.ollama_ import OllamaEmbedding
import os

emb = OllamaEmbedding(
    model=os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text"),
    base_url=os.getenv("OLLAMA_EMBEDDING_BASE_URL", "http://localhost:11434"),
)
vec = emb.embed_query("test")
assert isinstance(vec, list) and len(vec) > 0
print(f"Ollama Embedding ✓ (dim={len(vec)})")
```

---

### 2-D. AWS Bedrock Embedding

```
# .env
EMBEDDING_PROVIDER=bedrock
AWS_BEDROCK_EMBEDDING_ACCESS_KEY_ID=...
AWS_BEDROCK_EMBEDDING_SECRET_ACCESS_KEY=...
AWS_BEDROCK_EMBEDDING_REGION=us-east-1
AWS_BEDROCK_EMBEDDING_MODEL=amazon.titan-embed-text-v2:0
```

```python
from lang2sql.integrations.embedding.bedrock_ import BedrockEmbedding
import os

emb = BedrockEmbedding(
    model_id=os.getenv("AWS_BEDROCK_EMBEDDING_MODEL", "amazon.titan-embed-text-v2:0"),
    aws_access_key_id=os.getenv("AWS_BEDROCK_EMBEDDING_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_BEDROCK_EMBEDDING_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_BEDROCK_EMBEDDING_REGION", "us-east-1"),
)
vec = emb.embed_query("주문 데이터")
assert isinstance(vec, list) and len(vec) == 1024   # Titan v2 기본 차원
print(f"Bedrock Embedding ✓ (dim={len(vec)})")
```

---

### 2-E. Google Gemini Embedding

```
# .env
EMBEDDING_PROVIDER=gemini
GEMINI_EMBEDDING_API_KEY=AIza...
EMBEDDING_MODEL=models/embedding-001
```

```python
from lang2sql.integrations.embedding.gemini_ import GeminiEmbedding
import os

emb = GeminiEmbedding(
    model=os.getenv("EMBEDDING_MODEL", "models/embedding-001"),
    api_key=os.getenv("GEMINI_EMBEDDING_API_KEY"),
)
vec = emb.embed_query("주문 데이터")
assert isinstance(vec, list) and len(vec) == 768
print(f"Gemini Embedding ✓ (dim={len(vec)})")
```

---

### 2-F. HuggingFace Embedding (로컬 모델)

```
# .env
EMBEDDING_PROVIDER=huggingface
HUGGING_FACE_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

```python
# pip install sentence-transformers 필요
from lang2sql.integrations.embedding.huggingface_ import HuggingFaceEmbedding
import os

emb = HuggingFaceEmbedding(
    model=os.getenv("HUGGING_FACE_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
)
vec = emb.embed_query("주문 데이터")
assert isinstance(vec, list) and len(vec) == 384   # all-MiniLM-L6-v2 차원
print(f"HuggingFace Embedding ✓ (dim={len(vec)})")
```

---

## 3. 환경변수 기반 Factory (`build_*_from_env`)

`.env`에 원하는 프로바이더 설정을 넣고 아래를 실행합니다.

```python
from dotenv import load_dotenv
load_dotenv()

from lang2sql.factory import build_llm_from_env, build_embedding_from_env, build_db_from_env

# LLM
llm = build_llm_from_env()
resp = llm.invoke([{"role": "user", "content": "Say 'ready'"}])
assert isinstance(resp, str)
print(f"build_llm_from_env ✓ → {resp[:40]}")

# Embedding
emb = build_embedding_from_env()
vec = emb.embed_query("test")
assert isinstance(vec, list) and len(vec) > 0
print(f"build_embedding_from_env ✓ dim={len(vec)}")

# DB
db = build_db_from_env()
# DB_TYPE=sqlite 인 경우 간단한 쿼리 실행 확인
rows = db.execute("SELECT 1 AS val")
assert rows[0]["val"] == 1
print("build_db_from_env ✓")
```

---

## 4. 고급 컴포넌트 — 실제 LLM 호출

아래 예제는 Anthropic LLM으로 작성됐으나 어떤 프로바이더든 사용 가능합니다.

### 4-A. QuestionGate

```python
from dotenv import load_dotenv; load_dotenv()
from lang2sql.factory import build_llm_from_env
from lang2sql.components.gate.question_gate import QuestionGate
from lang2sql.core.catalog import GateResult

llm = build_llm_from_env()
gate = QuestionGate(llm=llm)

# 정상 쿼리 → suitable=True
result: GateResult = gate("지난달 주문 건수를 알려줘")
assert result.suitable is True, f"suitable False: {result.reason}"
print(f"QuestionGate (suitable) ✓ — reason: {result.reason}")

# 비적합 쿼리 → suitable=False
result2: GateResult = gate("회사 전략 보고서를 통계 모델로 분석해줘")
assert result2.suitable is False, "Expected unsuitable for data-science request"
print(f"QuestionGate (not suitable) ✓ — reason: {result2.reason}")
```

---

### 4-B. TableSuitabilityEvaluator

```python
from lang2sql.factory import build_llm_from_env
from lang2sql.components.gate.table_suitability import TableSuitabilityEvaluator

llm = build_llm_from_env()
evaluator = TableSuitabilityEvaluator(llm=llm)

catalog = [
    {"name": "orders", "description": "주문 정보 테이블", "columns": {"order_id": "주문 ID", "amount": "금액", "created_at": "생성일"}},
    {"name": "users", "description": "사용자 정보 테이블", "columns": {"user_id": "유저 ID", "name": "이름"}},
    {"name": "products", "description": "상품 정보 테이블", "columns": {"product_id": "상품 ID", "price": "가격"}},
]

filtered = evaluator("지난달 주문 건수", catalog)
# orders 테이블은 반드시 포함되어야 함
names = [t["name"] for t in filtered]
assert "orders" in names, f"orders not found in {names}"
print(f"TableSuitabilityEvaluator ✓ → {names}")
```

---

### 4-C. QuestionProfiler

```python
from lang2sql.factory import build_llm_from_env
from lang2sql.components.enrichment.question_profiler import QuestionProfiler
from lang2sql.core.catalog import QuestionProfile

llm = build_llm_from_env()
profiler = QuestionProfiler(llm=llm)

profile: QuestionProfile = profiler("월별 주문 금액 추이")
assert hasattr(profile, "is_timeseries")
assert hasattr(profile, "intent_type")
print(f"QuestionProfiler ✓ — is_timeseries={profile.is_timeseries}, intent={profile.intent_type}")

profile2: QuestionProfile = profiler("상위 10개 고객 목록")
assert hasattr(profile2, "has_ranking")
print(f"QuestionProfiler ✓ — has_ranking={profile2.has_ranking}")
```

---

### 4-D. ContextEnricher

```python
from lang2sql.factory import build_llm_from_env
from lang2sql.components.enrichment.context_enricher import ContextEnricher
from lang2sql.core.catalog import QuestionProfile

llm = build_llm_from_env()
enricher = ContextEnricher(llm=llm)

catalog = [
    {"name": "orders", "description": "주문 정보", "columns": {"order_id": "주문 ID", "amount": "금액", "created_at": "생성일"}},
]
profile = QuestionProfile(is_aggregation=True, has_filter=True, intent_type="lookup")
enriched = enricher("지난달 주문 건수", catalog, profile)

assert isinstance(enriched, str) and len(enriched) > 0
print(f"ContextEnricher ✓ — enriched: {enriched[:100]}")
```

---

## 5. HybridRetriever (BM25 + Vector RRF)

```python
from dotenv import load_dotenv; load_dotenv()
from lang2sql.factory import build_embedding_from_env
from lang2sql.components.retrieval.hybrid import HybridRetriever

emb = build_embedding_from_env()

catalog = [
    {"name": "orders", "description": "주문 정보 테이블", "columns": {"order_id": "주문 ID", "amount": "금액", "created_at": "생성일"}},
    {"name": "customers", "description": "고객 정보 테이블", "columns": {"customer_id": "고객 ID", "name": "이름", "email": "이메일"}},
    {"name": "products", "description": "상품 정보 테이블", "columns": {"product_id": "상품 ID", "price": "가격"}},
    {"name": "inventory", "description": "재고 테이블", "columns": {"product_id": "상품 ID", "stock": "재고 수량"}},
]

retriever = HybridRetriever(catalog=catalog, embedding=emb, top_n=2)
result = retriever("지난달 주문 건수")

assert len(result.schemas) <= 2
names = [s["name"] for s in result.schemas]
assert "orders" in names, f"orders missing from {names}"
print(f"HybridRetriever ✓ → schemas={names}")

# 비즈니스 문서 context 테스트
from lang2sql.core.catalog import TextDocument
docs = [TextDocument(id="doc1", content="주문은 created_at 컬럼 기준으로 집계합니다.")]
retriever2 = HybridRetriever(catalog=catalog, embedding=emb, documents=docs, top_n=2)
result2 = retriever2("주문 날짜 기준 집계")
print(f"HybridRetriever with docs ✓ — context={result2.context}")
```

---

## 6. BaselineNL2SQL — End-to-End

SQLite 예제 (가장 빠르게 검증 가능)

```bash
# 테스트 DB 준비
python - <<'EOF'
import sqlite3
conn = sqlite3.connect("test_e2e.db")
conn.execute("CREATE TABLE IF NOT EXISTS orders (order_id INTEGER PRIMARY KEY, amount REAL, created_at TEXT)")
conn.execute("INSERT OR IGNORE INTO orders VALUES (1, 10000, '2024-01-15')")
conn.execute("INSERT OR IGNORE INTO orders VALUES (2, 20000, '2024-01-20')")
conn.execute("INSERT OR IGNORE INTO orders VALUES (3, 15000, '2024-02-05')")
conn.commit()
conn.close()
print("test_e2e.db 생성 완료")
EOF
```

```python
from dotenv import load_dotenv; load_dotenv()
from lang2sql.factory import build_llm_from_env
from lang2sql.flows import BaselineNL2SQL
from lang2sql.integrations.db.sqlalchemy_ import SQLAlchemyDB

catalog = [
    {
        "name": "orders",
        "description": "주문 정보 테이블",
        "columns": {"order_id": "주문 ID", "amount": "주문 금액(원)", "created_at": "주문 생성일(YYYY-MM-DD)"},
    }
]

llm = build_llm_from_env()
db = SQLAlchemyDB("sqlite:///test_e2e.db")

pipeline = BaselineNL2SQL(catalog=catalog, llm=llm, db=db, db_dialect="sqlite")
rows = pipeline.run("전체 주문 건수")

assert isinstance(rows, list) and len(rows) > 0
print(f"BaselineNL2SQL ✓ — rows={rows}")
```

---

## 7. EnrichedNL2SQL — End-to-End (Full 7-Step Pipeline)

```python
from dotenv import load_dotenv; load_dotenv()
from lang2sql.factory import build_llm_from_env, build_embedding_from_env
from lang2sql.flows import EnrichedNL2SQL
from lang2sql.integrations.db.sqlalchemy_ import SQLAlchemyDB
from lang2sql.core.hooks import MemoryHook

catalog = [
    {
        "name": "orders",
        "description": "주문 정보 테이블. 고객이 결제한 주문 기록.",
        "columns": {"order_id": "주문 ID", "amount": "주문 금액(원)", "created_at": "주문 생성일(YYYY-MM-DD)"},
    }
]

llm = build_llm_from_env()
emb = build_embedding_from_env()
db = SQLAlchemyDB("sqlite:///test_e2e.db")
hook = MemoryHook()

pipeline = EnrichedNL2SQL(
    catalog=catalog,
    llm=llm,
    db=db,
    embedding=emb,
    db_dialect="sqlite",
    gate_enabled=True,
    top_n=3,
    hook=hook,
)

rows = pipeline.run("전체 주문 건수를 알려줘")
assert isinstance(rows, list) and len(rows) > 0
print(f"EnrichedNL2SQL ✓ — rows={rows}")

# Hook 이벤트 확인 (QuestionGate ~ SQLExecutor까지 7단계 이벤트 발생 확인)
components = {e.component for e in hook.events}
print(f"  → 실행된 컴포넌트: {components}")
assert "QuestionGate" in components
assert "HybridRetriever" in components
assert "SQLGenerator" in components
assert "SQLExecutor" in components
print("  → Hook 이벤트 ✓")
```

### 7-A. QuestionGate — ContractError 발생 확인

```python
from lang2sql.core.exceptions import ContractError
import pytest

try:
    pipeline.run("우리 회사 마케팅 전략을 ML 모델로 예측해줘")
    print("WARNING: ContractError가 발생해야 합니다")
except ContractError as e:
    print(f"ContractError ✓ — {e}")
```

### 7-B. gate_enabled=False — Gate 비활성화 확인

```python
pipeline_no_gate = EnrichedNL2SQL(
    catalog=catalog, llm=llm, db=db, embedding=emb,
    db_dialect="sqlite", gate_enabled=False,
)
rows2 = pipeline_no_gate.run("전체 주문 금액 합계")
assert isinstance(rows2, list)
print(f"EnrichedNL2SQL (no gate) ✓ — rows={rows2}")
```

---

## 8. CLI 명령어

`.env`가 올바르게 설정된 상태에서 실행합니다.

### 8-A. Baseline 플로우

```bash
lang2sql query "전체 주문 건수" \
  --flow baseline \
  --dialect sqlite
```

**예상 출력**: JSON 배열 (결과 행) 또는 `(결과 없음)`

---

### 8-B. Enriched 플로우

```bash
lang2sql query "지난 1월 주문 금액 합계" \
  --flow enriched \
  --dialect sqlite \
  --top-n 3
```

---

### 8-C. Gate 비활성화

```bash
lang2sql query "전체 주문 건수" \
  --flow enriched \
  --no-gate \
  --dialect sqlite
```

---

### 8-D. 에러 케이스 확인

```bash
# LLM_PROVIDER를 잘못된 값으로 설정한 경우
LLM_PROVIDER=unknown lang2sql query "test"
# 예상: ValueError: Unknown LLM_PROVIDER: 'unknown'
```

---

## 9. DataHub 카탈로그 브릿지

> DataHub GMS 서버가 실행 중이어야 합니다.

```
# .env
DATAHUB_SERVER=http://localhost:8080
```

```python
import os
from dotenv import load_dotenv; load_dotenv()
from lang2sql.integrations.catalog.datahub_ import DataHubCatalogLoader

loader = DataHubCatalogLoader(gms_server=os.getenv("DATAHUB_SERVER", "http://localhost:8080"))
catalog = loader.load()

assert isinstance(catalog, list)
assert len(catalog) > 0, "DataHub에 테이블이 하나 이상 존재해야 합니다"

first = catalog[0]
assert "name" in first and "description" in first and "columns" in first
print(f"DataHubCatalogLoader ✓ — {len(catalog)}개 테이블 로드")
print(f"  첫 번째: name={first['name']}, columns={list(first['columns'].keys())[:5]}")
```

### DataHub Catalog → EnrichedNL2SQL 연동

```python
from lang2sql.factory import build_llm_from_env, build_embedding_from_env, build_db_from_env

llm = build_llm_from_env()
emb = build_embedding_from_env()
db = build_db_from_env()
pipeline = EnrichedNL2SQL(
    catalog=catalog,   # DataHub에서 로드한 catalog 사용
    llm=llm, db=db, embedding=emb,
    gate_enabled=True,
)
rows = pipeline.run("유니크한 유저 수를 카운트해줘")
print(f"DataHub catalog + EnrichedNL2SQL ✓ — {rows}")
```

---

## 10. FAISSVectorStore (v2 벡터 스토어)

```python
from dotenv import load_dotenv; load_dotenv()
from lang2sql.factory import build_embedding_from_env
from lang2sql.integrations.vectorstore.faiss_ import FAISSVectorStore

emb = build_embedding_from_env()

# 문서 임베딩 및 저장
texts = ["주문 테이블: 고객 주문 정보를 저장합니다", "고객 테이블: 회원 정보를 저장합니다"]
vectors = emb.embed_texts(texts)

store = FAISSVectorStore(index_path="/tmp/test_faiss.idx")
store.upsert(ids=["doc0", "doc1"], vectors=vectors)

# 검색
query_vec = emb.embed_query("주문 정보")
results = store.search(query_vec, k=2)

assert len(results) > 0
assert results[0][0] in ["doc0", "doc1"]
print(f"FAISSVectorStore ✓ — top result: {results[0]}")

# 저장/로드
store.save()
loaded = FAISSVectorStore.load("/tmp/test_faiss.idx")
results2 = loaded.search(query_vec, k=1)
assert results2[0][0] == results[0][0]
print("FAISSVectorStore save/load ✓")
```

---

## 11. Streamlit UI 수동 검증

```bash
lang2sql run-streamlit
# 또는
streamlit run interface/streamlit_app.py
```

### 체크리스트

| 항목 | 확인 방법 | 통과 조건 |
|------|-----------|-----------|
| 홈 페이지 | `http://localhost:8501` 접속 | 에러 없이 로드 |
| Lang2SQL — Baseline | 워크플로우 체크박스 해제 → "쿼리 실행" | 결과 테이블 렌더링 |
| Lang2SQL — Enriched | 체크박스 선택 → "쿼리 실행" | 결과 테이블 렌더링 |
| Dialect 선택 | `sqlite` → `postgresql` 전환 | 드롭다운 변경 반영 |
| 오류 표시 | 연결 불가 DB 설정 후 실행 | `st.error()` 에러 박스 |
| ChatBot 페이지 | `🤖 ChatBot` 탭 클릭 | 에러 없이 로드 |
| 설정 페이지 | `⚙️ 설정` 탭 클릭 | 에러 없이 로드 |
| Graph Builder 페이지 없음 | 네비게이션 탭 확인 | 탭 목록에 없어야 함 |

---

## 12. ChatBot — LangGraph + 수정된 `search_database_tables`

> `DATAHUB_SERVER`가 설정되어 있어야 합니다. DataHub 없이 검색 시 에러 응답(`{"error": True, ...}`)을 반환합니다.

```python
import os
from dotenv import load_dotenv; load_dotenv()

# 12-A. 모듈 임포트 무결성 확인 (핵심: retrieval.py 삭제 이후 임포트 성공 확인)
from utils.llm.tools import search_database_tables, get_glossary_terms, get_query_examples
print("utils.llm.tools import ✓")

from utils.llm.chatbot import ChatBot
print("utils.llm.chatbot import ✓")

# 12-B. ChatBot 인스턴스 생성
bot = ChatBot(
    openai_api_key=os.getenv("OPEN_AI_KEY"),
    model_name="gpt-4o-mini",
    gms_server=os.getenv("DATAHUB_SERVER", "http://localhost:8080"),
)
print("ChatBot instance ✓")

# 12-C. 기본 대화 테스트
result = bot.chat("안녕하세요", thread_id="test-001")
last_msg = result["messages"][-1]
assert hasattr(last_msg, "content") and len(last_msg.content) > 0
print(f"ChatBot.chat() ✓ — 응답: {last_msg.content[:60]}")
```

### 12-D. `search_database_tables` 직접 호출 (DataHub 연결 시)

```python
# DataHub가 연결된 환경에서만 성공적인 결과 반환
result = search_database_tables.invoke({
    "query": "주문 테이블",
    "top_n": 3
})
# DataHub 연결 성공 시: {"orders": {"table_description": "...", ...}, ...}
# DataHub 연결 실패 시: {"error": True, "message": "..."}
print(f"search_database_tables ✓ — result keys: {list(result.keys())}")
```

---

## 13. 레거시 정리 (삭제 확인)

아래 모듈들은 마이그레이션에서 삭제되었습니다. **임포트 시 에러 발생이 정상**입니다.

```python
import importlib, sys

deleted_modules = [
    "engine",
    "engine.query_executor",
    "utils.llm.core.factory",
    "utils.llm.chains",
    "utils.llm.retrieval",
    "utils.llm.vectordb",
    "utils.llm.graph_utils",
    "utils.llm.output_schema",
]

for mod in deleted_modules:
    try:
        importlib.import_module(mod)
        print(f"WARNING: {mod} — 삭제되었어야 하지만 여전히 존재합니다")
    except (ImportError, ModuleNotFoundError):
        print(f"✓ {mod} 삭제 확인")
```

---

## 14. 전체 회귀 테스트

```bash
# 유닛 테스트 전체 실행 (145 passed, 6 skipped 예상)
pytest tests/ -v --tb=short

# 커버리지 포함
pytest tests/ --cov=src/lang2sql --cov-report=term-missing
```

**예상 결과**: 145 passed, 6 skipped (pgvector 관련 — 실제 PostgreSQL 없이는 skip)

---

## 15. DB 커넥터 검증

사용하는 DB에 맞게 `.env`를 설정하고 아래를 실행합니다.

```python
from dotenv import load_dotenv; load_dotenv()
from lang2sql.factory import build_db_from_env

db = build_db_from_env()

# 실제 테이블에서 데이터 조회
rows = db.execute("SELECT COUNT(*) AS cnt FROM 실제_테이블명")
assert isinstance(rows, list) and "cnt" in rows[0]
print(f"DB 연결 ✓ — count={rows[0]['cnt']}")
```

### 지원 DB 목록 및 `.env` 키

| DB | `DB_TYPE` | 필수 환경변수 |
|----|-----------|---------------|
| SQLite | `sqlite` | `SQLITE_PATH` |
| PostgreSQL | `postgresql` | `POSTGRESQL_HOST/PORT/USER/PASSWORD/DATABASE` |
| MySQL | `mysql` | `MYSQL_HOST/PORT/USER/PASSWORD/DATABASE` |
| MariaDB | `mariadb` | `MARIADB_HOST/PORT/USER/PASSWORD/DATABASE` |
| DuckDB | `duckdb` | `DUCKDB_PATH` |
| ClickHouse | `clickhouse` | `CLICKHOUSE_HOST/PORT/USER/PASSWORD/DATABASE` |
| Snowflake | `snowflake` | `SNOWFLAKE_USER/PASSWORD/ACCOUNT` |
| Oracle | `oracle` | `ORACLE_HOST/PORT/USER/PASSWORD/SERVICE_NAME` |

---

## 빠른 스모크 테스트 스크립트

아래 스크립트를 `smoke_test.py`로 저장 후 실행하면 가장 중요한 경로를 빠르게 확인할 수 있습니다.

```python
"""
smoke_test.py — 핵심 경로 빠른 검증 (Anthropic + SQLite 기준)
실행: python smoke_test.py
"""

import os
import sqlite3

from dotenv import load_dotenv
load_dotenv()

print("=" * 50)
print("Lang2SQL v2 Smoke Test")
print("=" * 50)

# 1. 테스트 DB
print("\n[1] SQLite DB 준비")
conn = sqlite3.connect("/tmp/smoke.db")
conn.execute("CREATE TABLE IF NOT EXISTS orders (id INT, amount REAL, created_at TEXT)")
conn.execute("DELETE FROM orders")
conn.executemany("INSERT INTO orders VALUES (?,?,?)", [
    (1, 10000, "2024-01-10"), (2, 20000, "2024-01-20"), (3, 15000, "2024-02-01")
])
conn.commit(); conn.close()
print("  ✓ /tmp/smoke.db")

# 2. Factory
print("\n[2] Factory 인스턴스 생성")
from lang2sql.factory import build_llm_from_env, build_embedding_from_env, build_db_from_env
llm = build_llm_from_env()
emb = build_embedding_from_env()
db  = build_db_from_env() if os.getenv("DB_TYPE") else None
print(f"  ✓ LLM={llm.__class__.__name__}, Embedding={emb.__class__.__name__}")

# 3. LLM 통신
print("\n[3] LLM 호출")
resp = llm.invoke([{"role": "user", "content": "Respond with OK"}])
assert isinstance(resp, str) and len(resp) > 0
print(f"  ✓ response={resp[:30]}")

# 4. BaselineNL2SQL
print("\n[4] BaselineNL2SQL")
from lang2sql.flows import BaselineNL2SQL
from lang2sql.integrations.db.sqlalchemy_ import SQLAlchemyDB

catalog = [{"name": "orders", "description": "주문 테이블", "columns": {"id": "주문 ID", "amount": "금액", "created_at": "생성일"}}]
pipe_base = BaselineNL2SQL(catalog=catalog, llm=llm, db=SQLAlchemyDB("sqlite:////tmp/smoke.db"), db_dialect="sqlite")
rows = pipe_base.run("전체 주문 건수")
assert isinstance(rows, list) and len(rows) > 0
print(f"  ✓ rows={rows}")

# 5. EnrichedNL2SQL
print("\n[5] EnrichedNL2SQL")
from lang2sql.flows import EnrichedNL2SQL

pipe_rich = EnrichedNL2SQL(
    catalog=catalog, llm=llm, embedding=emb,
    db=SQLAlchemyDB("sqlite:////tmp/smoke.db"),
    db_dialect="sqlite", gate_enabled=True,
)
rows2 = pipe_rich.run("주문 총 건수")
assert isinstance(rows2, list) and len(rows2) > 0
print(f"  ✓ rows={rows2}")

# 6. 삭제 확인
print("\n[6] 삭제된 레거시 모듈 확인")
import importlib
for m in ["utils.llm.retrieval", "utils.llm.vectordb", "utils.llm.chains"]:
    try:
        importlib.import_module(m)
        print(f"  WARNING: {m} 존재 — 삭제 필요")
    except (ImportError, ModuleNotFoundError):
        print(f"  ✓ {m} 삭제됨")

print("\n" + "=" * 50)
print("Smoke Test 완료")
print("=" * 50)
```

```bash
python smoke_test.py
```
