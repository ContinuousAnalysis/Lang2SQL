# 04. 하이브리드 검색 — BM25 + Vector

`HybridRetriever`는 BM25 키워드 검색과 벡터 유사도 검색을 RRF(Reciprocal Rank Fusion)로 결합합니다.
키워드 검색의 정확성과 벡터 검색의 의미 일반화를 모두 얻을 수 있습니다.

---

## 사전 준비

```bash
export OPENAI_API_KEY="sk-..."
python scripts/setup_sample_db.py
python scripts/setup_sample_docs.py
```

---

## 1) HybridNL2SQL — 가장 빠른 시작

`BaselineNL2SQL`에서 `embedding` 파라미터 하나만 추가합니다.

```python
from lang2sql import HybridNL2SQL
from lang2sql.integrations.db import SQLAlchemyDB
from lang2sql.integrations.embedding import OpenAIEmbedding
from lang2sql.integrations.llm import OpenAILLM

catalog = [
    {
        "name": "orders",
        "description": "고객 주문 정보. 주문 건수·금액·날짜 조회에 사용.",
        "columns": {
            "order_id":   "주문 고유 ID (PK)",
            "customer_id":"고객 ID (FK → customers)",
            "order_date": "주문 일시",
            "amount":     "주문 금액",
            "status":     "주문 상태: pending / confirmed / shipped / cancelled",
        },
    },
    {
        "name": "customers",
        "description": "고객 마스터. 이름·등급·가입일 조회에 사용.",
        "columns": {
            "customer_id": "고객 고유 ID (PK)",
            "name":        "고객 이름",
            "grade":       "고객 등급: bronze / silver / gold",
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

pipeline = HybridNL2SQL(
    catalog=catalog,
    llm=OpenAILLM(model="gpt-4o-mini"),
    db=SQLAlchemyDB("sqlite:///sample.db"),
    embedding=OpenAIEmbedding(model="text-embedding-3-small"),
    documents=docs,
    db_dialect="sqlite",
    top_n=5,
)

rows = pipeline.run("취소 제외한 이번 달 순매출 합계")
print(rows)
```

---

## 2) DirectoryLoader와 함께

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

rows = pipeline.run("gold 고객의 이번 달 주문 건수")
print(rows)
```

---

## 3) HybridRetriever 단독 사용

검색 결과만 먼저 확인하고 싶을 때:

```python
from lang2sql import HybridRetriever
from lang2sql.integrations.embedding import OpenAIEmbedding

retriever = HybridRetriever(
    catalog=catalog,
    embedding=OpenAIEmbedding(model="text-embedding-3-small"),
    documents=docs,
    top_n=5,
    rrf_k=60,            # RRF 상수. 높을수록 순위 간 점수 차이가 줄어듦
    score_threshold=0.0,
)

result = retriever.run("지난달 할인 매출")
print("schemas:", [s["name"] for s in result.schemas])
print("context:", result.context)
```

---

## 4) EnrichedNL2SQL — 풀 파이프라인

질문 적합성 검증, 테이블 필터링, 질문 프로파일링, 컨텍스트 보강까지 포함한 파이프라인입니다.

```
QuestionGate → HybridRetriever → TableSuitabilityEvaluator
  → QuestionProfiler → ContextEnricher → SQLGenerator → SQLExecutor
```

```python
from lang2sql import EnrichedNL2SQL
from lang2sql.integrations.db import SQLAlchemyDB
from lang2sql.integrations.embedding import OpenAIEmbedding
from lang2sql.integrations.llm import OpenAILLM

pipeline = EnrichedNL2SQL(
    catalog=catalog,
    llm=OpenAILLM(model="gpt-4o"),
    db=SQLAlchemyDB("sqlite:///sample.db"),
    embedding=OpenAIEmbedding(model="text-embedding-3-small"),
    documents=docs,
    db_dialect="sqlite",
    gate_enabled=True,   # QuestionGate 활성화 여부 (기본값: True)
    top_n=5,
)

rows = pipeline.run("이번 달 gold 고객의 순매출 합계")
print(rows)
```

### QuestionGate

`gate_enabled=True`(기본값)이면 SQL로 답할 수 없는 질문은 `ContractError`를 발생시킵니다.

```python
from lang2sql.core.exceptions import ContractError

try:
    rows = pipeline.run("오늘 날씨가 어때?")
except ContractError as e:
    print(f"SQL 생성 불가: {e}")
```

Gate가 불필요하면 `gate_enabled=False`로 비활성화합니다.

---

## 5) 파이프라인 선택 가이드

| 파이프라인 | 검색 방식 | 적합한 상황 |
|---|---|---|
| `BaselineNL2SQL` | BM25 키워드 | 빠른 시작, 카탈로그 규모 소~중간 |
| `HybridNL2SQL` | BM25 + Vector | 검색 품질 우선, 비즈니스 문서 활용 |
| `EnrichedNL2SQL` | BM25 + Vector + Gate | 운영 환경, 부적합 질문 필터링 필요 |

---

## 다음 단계

수동 컴포넌트 조합, 커스텀 어댑터, 관측성 → [05-advanced.md](./05-advanced.md)
