# 01. 빠른 시작 — 5분 안에 NL2SQL 실행하기

lang2sql v2의 기본 파이프라인을 실제 LLM과 DB로 바로 실행합니다.

---

## 사전 준비

```bash
pip install lang2sql
export OPENAI_API_KEY="sk-..."
```

샘플 DB 생성:

```bash
python scripts/setup_sample_db.py
```

완료되면 프로젝트 루트에 `sample.db`가 생성됩니다.

---

## BaselineNL2SQL 실행

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
            "name": "고객 이름",
            "grade": "고객 등급: bronze / silver / gold",
        },
    },
]

pipeline = BaselineNL2SQL(
    catalog=catalog,
    llm=OpenAILLM(model="gpt-4o-mini"),
    db=SQLAlchemyDB("sqlite:///sample.db"),
    db_dialect="sqlite",
)

rows = pipeline.run("지난달 주문 건수를 알려줘")
print(rows)
```

---

## 파이프라인 구조

```
BaselineNL2SQL
  ├── KeywordRetriever   — catalog에서 관련 테이블 검색 (BM25)
  ├── SQLGenerator       — LLM으로 SQL 생성
  └── SQLExecutor        — DB 실행 후 결과 반환
```

`BaselineNL2SQL`은 키워드 기반 검색(`KeywordRetriever`)을 사용합니다.
벡터 검색이 필요하면 `HybridNL2SQL`을 사용하세요 (→ [04-hybrid.md](./04-hybrid.md)).

---

## 지원 LLM

`LLMPort`를 만족하는 구현체로 교체할 수 있습니다.

```python
from lang2sql.integrations.llm import AnthropicLLM
llm = AnthropicLLM(model="claude-sonnet-4-6")

from lang2sql.integrations.llm import OpenAILLM
llm = OpenAILLM(model="gpt-4o")
```

둘 다 `LLMPort.invoke(messages)` 계약을 따르므로 파이프라인 코드는 동일합니다.

---

## 다음 단계

DB Explorer, 다중 테이블 카탈로그, 실제 운영 DB 연결 → [02-baseline.md](./02-baseline.md)
