## RunContext

`RunContext`는 define-by-run 파이프라인에서 **상태(state)를 운반하는 최소 State Carrier**입니다.
컴포넌트는 기본적으로 `RunContext -> RunContext` 계약을 따르며, 필요한 값을 읽고/쓰면서 파이프라인을 구성합니다.

### 설계 원칙

* **최소 루트 필드 5개만 고정**: `inputs / artifacts / outputs / error / metadata`
* 루트는 전부 `dict` 기반(스키마 락인 방지)
* 자주 쓰는 값은 **alias 프로퍼티**로 제공하여 UX 개선 (`run.query`, `run.sql` 등)

---

## 데이터 구조 트리

아래는 `RunContext`가 담는 데이터 구조를 “트리 형태”로 나타낸 것입니다.

```
RunContext
├─ inputs: dict
│  └─ "query": str
│
├─ artifacts: dict
│  └─ "schema": dict
│     ├─ "catalog": Any
│     │    (예: list[TableSchema] | provider | None)
│     ├─ "selected": Any
│     │    (예: list[TableCandidate] | None)
│     └─ "context": str
│          (prompt에 넣을 스키마 컨텍스트)
│
├─ outputs: dict
│  ├─ "sql": str
│  └─ "validation": Any
│
├─ error: dict | None
│  └─ (구조화된 에러 정보. 형식은 프로젝트 정책에 따라 확장 가능)
│
└─ metadata: dict
   └─ (로그/추적/히스토리/실험용 값. 표준 스키마 강제 없음)
      예)
      ├─ "events": list[Event]
      ├─ "sql_drafts": list[str]
      ├─ "attempt": int
      └─ ...
```

---

## Root fields (고정 5개)

* `inputs: dict[str, Any]` — 사용자 입력
* `artifacts: dict[str, Any]` — 중간 산출물
* `outputs: dict[str, Any]` — 최종 산출물
* `error: Optional[dict[str, Any]]` — 구조화된 에러(선택)
* `metadata: dict[str, Any]` — 로그/추적/히스토리(선택)

---

## 권장 키 컨벤션 (Minimal Standard)

### inputs

* `inputs["query"]`: 자연어 질의

### artifacts["schema"]

* `catalog`: 스키마 카탈로그(테이블/컬럼 목록 등)
* `selected`: 선택된 테이블 후보
* `context`: 프롬프트에 들어갈 스키마 컨텍스트 문자열

### outputs

* `outputs["sql"]`: 최종 SQL
* `outputs["validation"]`: 검증 결과(구조는 구현체 자유)

---

## Alias (Beginner-friendly API)

키 문자열 접근을 줄이기 위해 alias를 제공합니다.

* `run.query` ↔ `inputs["query"]`
* `run.sql` ↔ `outputs["sql"]`
* `run.validation` ↔ `outputs["validation"]`

스키마 관련 alias:

* `run.schema` ↔ `artifacts["schema"]` *(항상 dict로 보정)*
* `run.schema_catalog` ↔ `run.schema["catalog"]`
* `run.schema_selected` ↔ `run.schema["selected"]`
* `run.schema_context` ↔ `run.schema["context"]`

---

## 파이프라인 예시 (Text2SQL)

개념:

* retriever: `(query, catalog) -> selected`
* builder: `(query, selected) -> context`
* generator: `(query, context) -> sql`
* validator: `(sql) -> validation`

RunContext에서의 읽기/쓰기:

* retriever: `run.query`, `run.schema_catalog` 읽고 → `run.schema_selected` 작성
* builder: `run.query`, `run.schema_selected` 읽고 → `run.schema_context` 작성
* generator: `run.query`, `run.schema_context` 읽고 → `run.sql` 작성
* validator: `run.sql` 읽고 → `run.validation` 작성

---

