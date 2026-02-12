# BaseComponent

`BaseComponent`는 **define-by-run(순수 파이썬 제어)** 철학을 유지하면서도, 컴포넌트 실행을 **관측 가능(observable)** 하게 만들기 위한 **선택적(opt-in) 표준 레이어**입니다.

* 파이프라인은 `step(run: RunContext) -> RunContext` 형태의 **그냥 함수/콜러블**만으로도 충분히 동작합니다.
* `BaseComponent`는 그 위에 **추적(hooks), 에러 표준화, 이름/형식 통일**을 얹어주는 역할을 합니다.

즉, **필수는 아니지만**, 라이브러리/팀 단위 개발에서 “운영 가능한 형태”로 만들고 싶을 때 유용합니다.

---

## 왜 필요한가?

### 1) 관측성(Tracing)을 “그래프 엔진 없이” 얻기 위해

Lang2SQL은 LangGraph 같은 그래프 엔진을 강제하지 않습니다. 대신:

* 사용자는 Python `if/for/while`로 제어한다.
* 라이브러리는 관측성은 **hook 이벤트**로 제공한다.

`BaseComponent`는 각 컴포넌트 실행의 `start/end/error`를 이벤트로 남깁니다.

### 2) 에러를 “도메인 친화적으로” 정리하기 위해

현실에서는 `ValueError`, `KeyError`, 외부 라이브러리 예외 등이 섞여서 올라옵니다.

`BaseComponent`는:

* `Lang2SQLError`(ValidationError, IntegrationMissingError 등)는 **그대로 유지**
* 그 외 예외는 `ComponentError`로 **표준 래핑**(+ 원인 예외를 `cause`로 보존)

→ 사용자/운영자 관점에서 “어디서 터졌는지”가 분명해집니다.

### 3) “컴포넌트 단위 표준”을 만들기 위해

라이브러리 제공 컴포넌트를 모두 BaseComponent 기반으로 만들면:

* 로그/트레이스의 포맷이 통일
* 테스트/디버깅 경험이 일정
* 문서/타입 힌트가 일관

---

## 철학: Define-by-run + Minimal core

Lang2SQL의 기본 철학은 아래 2개입니다.

1. **제어는 파이썬으로**
   루프/분기/재시도/서브플로우 호출은 “프레임워크 DSL”이 아니라 Python으로 표현합니다.

2. **상태는 RunContext 하나로**
   파이프라인이 커져도, step 간 연결이 깨지지 않도록 `RunContext`를 I/O로 둡니다.

`BaseComponent`는 이 철학을 해치지 않습니다.
컴포넌트의 실행을 감싸서 이벤트만 남길 뿐, 그래프/스키마/실행 모델을 강제하지 않습니다.

---

## BaseComponent가 제공하는 API

### 생성자

```python
BaseComponent(name: str | None = None, hook: TraceHook | None = None)
```

* `name`: 이벤트에 찍힐 컴포넌트 이름 (기본값: 클래스명)
* `hook`: 이벤트 수신자. 기본값은 `NullHook()` (아무것도 하지 않음)

### 구현해야 하는 것: `run()`

```python
class MyComp(BaseComponent):
    def run(self, run: RunContext) -> RunContext:
        ...
        return run
```

### 실행: `__call__`

`comp(run)`을 호출하면 내부적으로 아래를 자동 수행합니다.

* `component.run start 이벤트 발행`
* `self.run(...)` 실행
* 성공 시 `end 이벤트` + `duration_ms`
* 실패 시 `error 이벤트`

  * 도메인 예외(`Lang2SQLError`)는 그대로 raise
  * 그 외 예외는 `ComponentError`로 래핑해서 raise

---

## 권장 규약: RunContext in → RunContext out

Lang2SQL의 기본 step 규약은 단순합니다.

> **RunContext를 받으면 RunContext를 반환한다.**
> (`return run`을 습관처럼)

왜냐하면 “None 반환”은 인간이 보기엔 자연스럽지만, 팀/사용자 관점에서는 실수를 만들기 쉽습니다.

* `return None`은 “의도적”인지 “실수(반환 누락)”인지 구분이 안 됨
* Flow/컴포넌트 조합에서 결과가 조용히 깨지기 쉬움

그래서 Lang2SQL은 **fail-fast** 스타일을 권장합니다.

---

## 언제 BaseComponent를 쓰는가?

### ✅ BaseComponent를 쓰는 게 좋은 경우

* 라이브러리 기본 제공 컴포넌트( retriever/builder/generator/validator )
* 팀/제품 환경에서 **관측성(트레이싱)이 필요한 경우**
* 예외 표준화가 중요한 경우(운영/테스트/디버깅)

### ✅ BaseComponent 없이 함수로 두는 게 좋은 경우

* `policy`, `eval`, metric 계산처럼 **순수 함수 성격**이 강한 로직
* “유저가 빠르게 붙여 넣어 쓰는” 초경량 커스텀 로직
* 실행 단위가 너무 작아 이벤트가 과도해지는 경우

즉, **핵심 파이프라인 축**은 BaseComponent로 잡고,
그 외의 작은 로직은 함수로 두는 혼합형이 가장 자연스럽습니다.

---

## FunctionalComponent: “함수도 트레이싱하고 싶다”

유저에게 “클래스 상속 + run 메서드 작성”이 부담인 경우가 많습니다.
그래서 **함수/콜러블을 그대로 유지하면서**도 트레이싱을 얻고 싶다면 래퍼를 제공합니다.

### 예시: FunctionalComponent

```python
from __future__ import annotations
from typing import Callable, Any, Optional

from .base import BaseComponent
from .context import RunContext

class FunctionalComponent(BaseComponent):
    """
    Wrap a callable(run: RunContext) -> RunContext into a BaseComponent,
    so it becomes traceable and error-normalized.
    """

    def __init__(
        self,
        fn: Callable[[RunContext], RunContext],
        *,
        name: str | None = None,
        hook=None,
    ) -> None:
        super().__init__(name=name or getattr(fn, "__name__", "FunctionalComponent"), hook=hook)
        self._fn = fn

    def run(self, run: RunContext) -> RunContext:
        return self._fn(run)
```

### 사용 예

```python
def my_retriever(run: RunContext) -> RunContext:
    run.schema_selected = ...
    return run

retriever = FunctionalComponent(my_retriever, name="MyRetriever", hook=hook)
```

> 이 방식의 장점: 유저는 “함수 스타일” 그대로 유지하면서, 운영/디버깅을 위한 트레이싱을 얻게 됩니다.

---

## 훅(Tracing) 시스템이 뭐고, 왜 필요한가?

### Hook이란?

컴포넌트/플로우 실행 시점에 **이벤트(Event)** 를 받는 인터페이스입니다.

* `start/end/error` 시점 기록
* 소요 시간(duration_ms)
* 입력/출력 요약(input_summary/output_summary)
* 필요하면 `data`에 구조화된 값을 추가

### 어디서 확인하나?

가장 쉬운 건 `MemoryHook`입니다.

```python
from lang2sql.core.hooks import MemoryHook
hook = MemoryHook()

flow = BaselineFlow(steps=[...], hook=hook)  # 또는 컴포넌트마다 hook 주입
out = flow.run_query("지난달 매출")

# 이벤트 확인
for e in hook.events:
    print(e.phase, e.component, e.duration_ms, e.error)
```

### 운영용 관측성은 어디서 제어하나?

운영에서는 `MemoryHook` 대신 다음이 일반적입니다.

* 로그로 흘리는 Hook (stdout / JSON log)
* APM/Tracing으로 보내는 Hook (OpenTelemetry span 등)
* 필터링 Hook (특정 컴포넌트만 샘플링)

핵심은: **관측성은 hook 구현체에서 제어**하고, 파이프라인/컴포넌트 코드는 최대한 “비즈니스 로직”만 갖도록 분리합니다.

---

## 중첩(서브플로우/래핑)하면 트레이싱이 깨지나?

“깨진다”기보다는 **이벤트가 더 많이 찍힙니다.**

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

### 1) 구성(config)은 `__init__`에, 요청별 상태는 `RunContext`에

```python
class Retriever(BaseComponent):
    def __init__(self, catalog, top_k=8, ...):
        self.catalog = catalog     # 고정 설정
        self.top_k = top_k

    def run(self, run: RunContext) -> RunContext:
        # 요청마다 달라지는 값은 run에서 읽고 run에 쓴다
        ...
        return run
```

### 2) RunContext가 들어오면 무조건 `return run`

* 가독성(계약이 분명)
* 실수 방지(fail-fast)
* flow 합성 시 안정

### 3) “작은 로직(policy/eval)은 그냥 함수”

* BaseComponent로 감싸는 건 선택
* 운영에서 꼭 추적이 필요할 때만 FunctionalComponent로 감싼다

---

## FAQ

### Q. “그냥 함수만 써도 되는데 왜 굳이 BaseComponent?”

A. **운영/디버깅/협업에서** 차이가 큽니다.
문제 났을 때 “어디서, 어떤 입력으로, 얼마나 걸리다, 어떤 에러로” 터졌는지 자동으로 남는 게 핵심 가치입니다.

### Q. “BaseComponent를 유저가 직접 써야 하나?”

A. 필수 아닙니다.
초급 유저는 **SequentialFlow + 프리셋 컴포넌트**만으로 충분히 쓰게 하고,
고급/운영 유저에게 BaseComponent/Hook을 제공하는 구성이 가장 자연스럽습니다.

### Q. “policy는 RunContext를 몰라도 되는데?”

A. 맞습니다. `policy(metrics) -> action` 같은 건 순수 함수로 두는 걸 권장합니다.
필요하면 `FunctionalComponent(policy_fn)`처럼 감싸서 추적만 추가할 수 있습니다.

---
