# BaseComponent

`BaseComponent`는 **define-by-run(순수 파이썬 제어)** 철학을 유지하면서도, 컴포넌트 실행을 **관측 가능(observable)** 하게 만들기 위한 **선택적(opt-in) 표준 레이어**입니다.

* 파이프라인은 그냥 함수/콜러블만으로도 충분히 동작합니다.
* `BaseComponent`는 그 위에 **추적(hooks), 에러 표준화, 이름/형식 통일**을 얹어주는 역할을 합니다.

즉, **필수는 아니지만**, 라이브러리/팀 단위 개발에서 "운영 가능한 형태"로 만들고 싶을 때 유용합니다.

---

## 왜 필요한가?

### 1) 관측성(Tracing)을 "그래프 엔진 없이" 얻기 위해

Lang2SQL은 그래프 엔진을 강제하지 않습니다. 대신:

* 사용자는 Python `if/for/while`로 제어한다.
* 라이브러리는 관측성은 **hook 이벤트**로 제공한다.

`BaseComponent`는 각 컴포넌트 실행의 `start/end/error`를 이벤트로 남깁니다.

### 2) 에러를 "도메인 친화적으로" 정리하기 위해

현실에서는 `ValueError`, `KeyError`, 외부 라이브러리 예외 등이 섞여서 올라옵니다.

`BaseComponent`는:

* `Lang2SQLError`(ValidationError, IntegrationMissingError 등)는 **그대로 유지**
* 그 외 예외는 `ComponentError`로 **표준 래핑**(+ 원인 예외를 `cause`로 보존)

→ 사용자/운영자 관점에서 "어디서 터졌는지"가 분명해집니다.

### 3) "컴포넌트 단위 표준"을 만들기 위해

라이브러리 제공 컴포넌트를 모두 BaseComponent 기반으로 만들면:

* 로그/트레이스의 포맷이 통일
* 테스트/디버깅 경험이 일정
* 문서/타입 힌트가 일관

---

## BaseComponent가 제공하는 API

### 생성자

```python
BaseComponent(name: str | None = None, hook: TraceHook | None = None)
```

* `name`: 이벤트에 찍힐 컴포넌트 이름 (기본값: 클래스명)
* `hook`: 이벤트 수신자. 기본값은 `NullHook()` (아무것도 하지 않음)

### 구현해야 하는 것: `_run()`

서브클래스는 `_run()`을 구현합니다. 인자 타입과 반환 타입은 각 컴포넌트에 맞게 자유롭게 정의합니다.

```python
class MyRetriever(BaseComponent):
    def __init__(self, catalog: list, **kwargs):
        super().__init__(**kwargs)
        self._catalog = catalog

    def _run(self, query: str) -> list[dict]:
        # 비즈니스 로직
        return [t for t in self._catalog if query in t["description"]]
```

### 호출: `run()` / `__call__`

`comp.run(query)` 또는 `comp(query)`를 호출하면 내부적으로 아래를 자동 수행합니다.

* `component.run start 이벤트 발행`
* `self._run(...)` 실행
* 성공 시 `end 이벤트` + `duration_ms`
* 실패 시 `error 이벤트`

  * 도메인 예외(`Lang2SQLError`)는 그대로 raise
  * 그 외 예외는 `ComponentError`로 래핑해서 raise

---

## 타입 인자 패턴

Lang2SQL의 컴포넌트는 **명시적 타입 인자**를 받고, **명시적 타입 결과**를 반환합니다.

```python
# 라이브러리 내장 컴포넌트 시그니처 예시
KeywordRetriever._run(query: str) -> list[CatalogEntry]
SQLGenerator._run(query: str, schemas: list[CatalogEntry], context: str = "") -> str
SQLExecutor._run(sql: str) -> list[dict]
```

### 구성(config)은 `__init__`에, 요청별 데이터는 `_run()` 인자에

```python
class SQLGenerator(BaseComponent):
    def __init__(self, llm: LLMPort, db_dialect: str = "default", **kwargs):
        super().__init__(**kwargs)
        self._llm = llm           # 고정 설정
        self._dialect = db_dialect

    def _run(self, query: str, schemas: list[CatalogEntry], context: str = "") -> str:
        # 요청마다 달라지는 값은 _run() 인자로 받는다
        ...
```

---

## 언제 BaseComponent를 쓰는가?

### BaseComponent를 쓰는 게 좋은 경우

* 라이브러리 기본 제공 컴포넌트(retriever/generator/executor)
* 팀/제품 환경에서 **관측성(트레이싱)이 필요한 경우**
* 예외 표준화가 중요한 경우(운영/테스트/디버깅)

### BaseComponent 없이 함수로 두는 게 좋은 경우

* `policy`, `eval`, metric 계산처럼 **순수 함수 성격**이 강한 로직
* "유저가 빠르게 붙여 넣어 쓰는" 초경량 커스텀 로직
* 실행 단위가 너무 작아 이벤트가 과도해지는 경우

즉, **핵심 파이프라인 축**은 BaseComponent로 잡고,
그 외의 작은 로직은 함수로 두는 혼합형이 가장 자연스럽습니다.

---

## 커스텀 컴포넌트 예시

```python
from lang2sql.core.base import BaseComponent

class UpperCaseSQL(BaseComponent):
    """SQL을 대문자로 변환하는 후처리 컴포넌트."""
    def _run(self, sql: str) -> str:
        return sql.upper()

upper = UpperCaseSQL()
print(upper.run("select 1"))  # SELECT 1
```

hook을 주입하면 실행 추적도 자동으로 됩니다:

```python
from lang2sql import MemoryHook

hook = MemoryHook()
upper = UpperCaseSQL(hook=hook)
upper.run("select 1")

for e in hook.snapshot():
    print(e.component, e.phase, e.duration_ms)
# UpperCaseSQL start 0.0
# UpperCaseSQL end   0.1
```

---

## 훅(Tracing) 시스템

### Hook이란?

컴포넌트/플로우 실행 시점에 **이벤트(Event)** 를 받는 인터페이스입니다.

* `start/end/error` 시점 기록
* 소요 시간(duration_ms)
* 입력/출력 요약(input_summary/output_summary)

### 어디서 확인하나?

가장 쉬운 건 `MemoryHook`입니다.

```python
from lang2sql import MemoryHook, HybridNL2SQL

hook = MemoryHook()
pipeline = HybridNL2SQL(catalog=catalog, llm=llm, db=db, embedding=embedding, hook=hook)
pipeline.run("지난달 매출")

for e in hook.snapshot():
    print(e.phase, e.component, e.duration_ms, e.error)
```

### 운영용 관측성은 어디서 제어하나?

운영에서는 `MemoryHook` 대신 다음이 일반적입니다.

* 로그로 흘리는 Hook (stdout / JSON log)
* APM/Tracing으로 보내는 Hook (OpenTelemetry span 등)
* 필터링 Hook (특정 컴포넌트만 샘플링)

핵심은: **관측성은 hook 구현체에서 제어**하고, 파이프라인/컴포넌트 코드는 최대한 "비즈니스 로직"만 갖도록 분리합니다.

---

## 중첩(서브플로우/래핑)하면 트레이싱이 깨지나?

"깨진다"기보다는 **이벤트가 더 많이 찍힙니다.**

* `flow_b` 안에 `flow_a`를 step으로 넣으면

  * `flow_b` 이벤트 2개(시작/끝)
  * `flow_a` 이벤트 2개(시작/끝)
  * `a1/a2` 컴포넌트 이벤트도 각각 찍힘(컴포넌트가 BaseComponent라면)

이게 싫다면 두 가지 선택지가 있습니다.

1. **상위 레벨(Flow)만 트레이싱하고 내부는 함수로 둔다**
2. **Hook에서 필터링/샘플링한다** (예: component 이름 prefix로 제외)

추가 문법 없이 해결하려면 2번이 가장 현실적입니다.

---

## 베스트 프랙티스

### 1) 구성(config)은 `__init__`에, 요청별 데이터는 `_run()` 인자에

고정 설정(모델, 카탈로그, DB 연결 등)은 생성자에서 받고,
요청마다 달라지는 값(쿼리, 스키마 목록 등)은 `_run()` 인자로 전달합니다.

### 2) `_run()`의 반환값은 명시적으로

반환 타입을 명확히 정의하면 Flow에서 컴포넌트를 조합할 때 안전합니다.

### 3) "작은 로직(policy/eval)은 그냥 함수"

* BaseComponent로 감싸는 건 선택
* 운영에서 꼭 추적이 필요할 때만 감싼다

---

## FAQ

### Q. "그냥 함수만 써도 되는데 왜 굳이 BaseComponent?"

A. **운영/디버깅/협업에서** 차이가 큽니다.
문제 났을 때 "어디서, 어떤 입력으로, 얼마나 걸리다, 어떤 에러로" 터졌는지 자동으로 남는 게 핵심 가치입니다.

### Q. "BaseComponent를 유저가 직접 써야 하나?"

A. 필수 아닙니다.
초급 유저는 **프리셋 Flow + 프리셋 컴포넌트**만으로 충분히 쓰게 하고,
고급/운영 유저에게 BaseComponent/Hook을 제공하는 구성이 가장 자연스럽습니다.

---
