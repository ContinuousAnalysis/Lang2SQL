# Core Concepts

Lang2SQL은 "그래프 엔진/DSL"을 강제하지 않고, **순수 Python 코드로 파이프라인을 제어**하는 define-by-run 철학을 따릅니다.
각 컴포넌트는 **명시적 타입 인자**를 받고, 명시적 타입 결과를 반환합니다.

---

## 1) Define-by-run: 제어는 Python으로

Lang2SQL에서 파이프라인 제어는 프레임워크가 아니라 **사용자 코드가 가집니다.**

* 분기: `if / match`
* 반복/재시도: `for / while`
* 조건부 실행: policy 기반 action
* 서브플로우: flow를 step처럼 호출

예시:

```python
retriever = KeywordRetriever(catalog=catalog)
generator = SQLGenerator(llm=llm, db_dialect="sqlite")

while True:
    schemas = retriever.run(query)
    sql = generator.run(query, schemas)
    if validator(sql):
        break

rows = executor.run(sql)
```

**핵심:** Lang2SQL은 위 패턴을 "프레임워크 문법"으로 바꾸지 않습니다.
그냥 Python으로 쓰되, 각 컴포넌트의 입출력이 **타입으로 명확히 정의**되어 있어 안전하게 조합할 수 있습니다.

---

## 2) 타입 인자 패턴

Text2SQL 파이프라인은 현실적으로 단계가 늘어납니다.

* retriever 1개가 아니라 10개, 100개가 될 수 있음
* 중간 산출물(선택된 테이블, 컨텍스트, 후보 SQL, 검증 결과, 점수/메트릭)이 늘어남
* loop/branch가 들어가면서 "어떤 단계에서 무엇이 생성되었는지" 추적이 어려워짐

Lang2SQL은 각 컴포넌트의 `_run()` 메서드가 **명시적 타입 인자를 받고 타입 결과를 반환**하도록 설계합니다.

```
KeywordRetriever._run(query: str) -> list[CatalogEntry]
SQLGenerator._run(query: str, schemas: list[CatalogEntry], context: str) -> str
SQLExecutor._run(sql: str) -> list[dict]
```

이 방식의 장점:

* 각 컴포넌트의 입출력이 코드에 명확히 드러남
* IDE 자동완성과 타입 체크를 활용할 수 있음
* 컴포넌트를 독립적으로 테스트하기 쉬움

### 컴포넌트 간 데이터 전달

컴포넌트 간 와이어링은 **전용 Flow가 내부에서 처리**합니다.

```python
# BaselineNL2SQL._run() 내부 구현
def _run(self, query: str) -> list[dict]:
    schemas = self._retriever(query)        # list[CatalogEntry]
    sql = self._generator(query, schemas)   # str
    return self._executor(sql)              # list[dict]
```

사용자 관점에서는 Flow의 `run()` 하나만 호출하면 됩니다:

```python
rows = pipeline.run("지난달 매출")
```

---

## 3) 컴포넌트 vs 플로우

| | BaseComponent | BaseFlow |
|---|---|---|
| 역할 | 단일 작업 단위 (검색, 생성, 실행) | 여러 컴포넌트의 조합/제어 |
| 구현 | `_run()` 메서드 | `_run()` 메서드 |
| 관측성 | `component.run` 이벤트 | `flow.run` 이벤트 |
| 예시 | `KeywordRetriever`, `SQLGenerator` | `BaselineNL2SQL`, `HybridNL2SQL` |

둘 다 **`_run()`에 비즈니스 로직**을 작성하고, `run()` / `__call__()` 호출 시 자동으로 hook 이벤트를 발행합니다.

---

## 권장 규약 요약

* **제어는 Python으로 한다** (define-by-run)
* **컴포넌트의 입출력은 명시적 타입 인자로 정의한다** (`_run(query: str) -> list[CatalogEntry]`)
* **구성(config)은 `__init__`에, 요청별 데이터는 `_run()` 인자에**
* policy/eval처럼 관측성이 불필요한 로직은 **순수 함수로 둬도 된다**

---
