# BaseFlow

`BaseFlow`는 Lang2SQL에서 **define-by-run(순수 파이썬 제어)** 철학을 구현하기 위한 "플로우의 최소 추상화(minimal abstraction)"입니다.

* 파이프라인의 **제어권(control-flow)** 을 프레임워크 DSL이 아니라 **사용자 코드(Python)** 가 갖습니다.
* 그래프 엔진을 강제하지 않습니다.
* 대신, 실행 단위를 `Flow`로 묶고 **관측성(hooks)** 과 **에러 규약**을 통일합니다.

---

## 왜 필요한가?

### 1) "제어는 파이썬으로"를 지키기 위해

Text2SQL은 현실적으로 다음 제어가 자주 필요합니다.

* 재시도 루프 (`while`, `for`)
* 조건 분기 (`if`, `match`)
* 부분 파이프라인(서브플로우) 호출
* 정책(policy) 기반 행동 결정

`BaseFlow`는 이런 제어를 **사용자가 Python으로 직접 작성**하게 두고, 라이브러리는 "실행 컨테이너 + 관측성"만 제공합니다.

### 2) 요청 단위 관측성(Flow-level tracing)

운영/디버깅에서는 "이 요청 전체가 언제 시작했고, 어디서 실패했고, 얼마나 걸렸는지"가 먼저 중요합니다.

`BaseFlow`는 다음 이벤트를 발행합니다.

* `flow.run` start / end / error
* 실행 시간(`duration_ms`)

→ 요청 1건을 **Flow 단위로 빠르게 파악**할 수 있습니다.

---

## BaseFlow가 제공하는 API

### 1) 구현해야 하는 것: `_run()`

```python
class MyFlow(BaseFlow):
    def _run(self, query: str) -> list[dict]:
        ...
        return result
```

* Flow의 본체 로직은 여기에 작성합니다.
* 제어는 Python으로 직접 작성합니다. (`if/for/while`)
* 입출력 타입은 자유롭게 정의합니다.

### 2) 호출: `run()` / `__call__`

```python
out = flow.run("지난달 매출")
# 또는
out = flow("지난달 매출")
```

* 내부적으로 `_run(...)`을 호출합니다.
* hook 이벤트를 `start/end/error`로 기록합니다.

---

## 사용 패턴

### 1) 초급: 프리셋 Flow로 바로 실행

초급 사용자는 보통 "구성만 하고 실행"하면 됩니다.

```python
pipeline = BaselineNL2SQL(catalog=catalog, llm=llm, db=db)
rows = pipeline.run("지난달 매출")
```

### 2) 고급: CustomFlow로 제어(while/if/policy)

정책/루프/재시도 같은 제어가 들어오면 `BaseFlow`를 직접 상속해 작성하는 것이 가장 깔끔합니다.

```python
class RetryFlow(BaseFlow):
    def _run(self, query: str) -> str:
        for _ in range(3):
            schemas = retriever(query)
            sql = generator(query, schemas)
            if validator(sql):
                return sql
        return sql
```

---

## Hook(Tracing)은 어디서 확인하나?

Flow도 hook을 받을 수 있습니다.

```python
from lang2sql import MemoryHook, BaselineNL2SQL

hook = MemoryHook()
pipeline = BaselineNL2SQL(catalog=catalog, llm=llm, db=db, hook=hook)

rows = pipeline.run("지난달 매출")

for e in hook.snapshot():
    print(e.name, e.phase, e.component, e.duration_ms, e.error)
```

운영에서는 `MemoryHook` 대신 로그/OTel/필터링 훅을 사용합니다.
관측성 제어는 **hook 구현체에서** 담당하고, Flow 코드는 비즈니스 로직에 집중하도록 분리합니다.

---

## (관련 개념) BaseFlow와 BaseComponent의 관계

* `BaseFlow`는 "어떻게 실행할지(제어/조립)"를 담당합니다.
* `BaseComponent`는 "한 단계에서 무엇을 할지(작업 단위)"를 담당합니다.

일반적으로:

* **Flow는 여러 Component를 호출**합니다.
* **전용 Flow(BaselineNL2SQL 등)는 Component 간 와이어링을 내부에서 처리**합니다.

즉, **Flow가 상위 레벨 오케스트레이션**, Component가 **재사용 가능한 부품**입니다.

---

## SequentialFlow의 알려진 제한

`SequentialFlow`는 `value = step(value)` 단일 값 전달 방식으로 동작합니다.
이 설계는 단순한 변환 체인에는 적합하지만, NL2SQL 파이프라인에서 다음 한계가 있습니다.

### 문제 1: 컨텍스트 소실

파이프라인이 진행되면서 초기 입력(`query`)이 중간 단계 출력으로 대체되어 사라집니다.

```python
flow.run("주문 내역 확인")
↓
retriever("주문 내역 확인")  →  list[CatalogEntry]
↓
generator(list[CatalogEntry])  # ← 여기서 original query가 없음
↓
TypeError 또는 잘못된 결과
```

### 문제 2: 다중 인자 컴포넌트와 호환 불가

`SQLGenerator._run(query, schemas)`처럼 2개 이상의 인자를 받는 컴포넌트는
`SequentialFlow`의 단일 값 전달로 연결할 수 없습니다.

```python
# ❌ 동작하지 않음 — generator는 (query, schemas) 2개 인자가 필요
flow = SequentialFlow(steps=[retriever, generator, executor])
flow.run("주문 내역")  # TypeError: _run() missing 1 required positional argument: 'schemas'
```

### 해결 방법

NL2SQL 파이프라인은 `SequentialFlow` 대신 **전용 Flow**를 사용하세요.
전용 Flow는 내부에서 다중 인자 와이어링을 올바르게 처리합니다.

```python
# KeywordRetriever 기반
pipeline = BaselineNL2SQL(catalog=catalog, llm=llm, db=db)

# Keyword + Vector 기반
pipeline = HybridNL2SQL(catalog=catalog, llm=llm, db=db, embedding=embedding)

# Gate + 프로파일링 + 보강 포함 풀 파이프라인
pipeline = EnrichedNL2SQL(catalog=catalog, llm=llm, db=db, embedding=embedding)

rows = pipeline.run("주문 내역")
```

`SequentialFlow`는 단일 값 변환 체인(예: 텍스트 전처리, 단계별 필터링)에 적합합니다.

---

## FAQ

### Q. BaseFlow가 필수인가?

A. Flow라는 개념은 사실상 필요하지만, **모든 사용자가 BaseFlow를 직접 상속할 필요는 없습니다.**

* 초급: 프리셋 Flow(`BaselineNL2SQL`, `HybridNL2SQL`, `EnrichedNL2SQL`)만 사용
* 고급: `BaseFlow`를 상속해서 제어를 직접 작성

### Q. Flow의 반환 타입은?

A. `_run()`의 입출력 타입은 자유롭습니다. 컴포넌트끼리 합의한 타입을 그대로 사용하면 됩니다.
