# BaseFlow

`BaseFlow`는 Lang2SQL에서 **define-by-run(순수 파이썬 제어)** 철학을 구현하기 위한 “플로우의 최소 추상화(minimal abstraction)”입니다.

* 파이프라인의 **제어권(control-flow)** 을 프레임워크 DSL이 아니라 **사용자 코드(Python)** 가 갖습니다.
* LangGraph 같은 그래프 엔진을 강제하지 않습니다.
* 대신, 실행 단위를 `Flow`로 묶고 **관측성(hooks)** 과 **에러 규약**을 통일합니다.

---

## 왜 필요한가?

### 1) “제어는 파이썬으로”를 지키기 위해

Text2SQL은 현실적으로 다음 제어가 자주 필요합니다.

* 재시도 루프 (`while`, `for`)
* 조건 분기 (`if`, `match`)
* 부분 파이프라인(서브플로우) 호출
* 정책(policy) 기반 행동 결정

`BaseFlow`는 이런 제어를 **사용자가 Python으로 직접 작성**하게 두고, 라이브러리는 “실행 컨테이너 + 관측성”만 제공합니다.

### 2) 요청 단위 관측성(Flow-level tracing)

운영/디버깅에서는 “이 요청 전체가 언제 시작했고, 어디서 실패했고, 얼마나 걸렸는지”가 먼저 중요합니다.

`BaseFlow`는 다음 이벤트를 발행합니다.

* `flow.run` start / end / error
* 실행 시간(`duration_ms`)

→ 요청 1건을 **Flow 단위로 빠르게 파악**할 수 있습니다.

### 3) 공통 엔트리포인트(run_query) 제공

Text2SQL은 대부분 “문장(query)”이 시작점입니다.

`run_query("...")`를 제공하면:

* 초급 사용자는 `RunContext`를 몰라도 “바로 실행” 가능
* 고급 사용자는 `run(RunContext)`로 제어를 확장 가능

---

## BaseFlow가 제공하는 API

### 1) 구현해야 하는 것: `run()`

```python
class MyFlow(BaseFlow):
    def run(self, run: RunContext) -> RunContext:
        ...
        return run
```

* Flow의 본체 로직은 여기에 작성합니다.
* 제어는 Python으로 직접 작성합니다. (`if/for/while`)

### 2) 호출: `__call__`

```python
out = flow(run)
```

* 내부적으로 `flow.run(...)`을 호출합니다.
* hook 이벤트를 `start/end/error`로 기록합니다.

### 3) 편의 엔트리포인트: `run_query()`

```python
out = flow.run_query("지난달 매출")
```

* 내부에서 `RunContext(query=...)`를 만들고 `run()`을 호출합니다.
* Quickstart / demo / 초급 UX용 엔트리포인트입니다.

> 권장: **BaseFlow에 run_query를 둬서 “모든 Flow는 run_query가 된다”는 직관을 유지**합니다.

---

## run(runcontext) vs run_query(query)

둘은 기능적으로 **같은 동작**을 하도록 설계합니다.

```python
out1 = flow.run_query("지난달 매출")
out2 = flow.run(RunContext(query="지난달 매출"))
```

* `run_query(query)` : 문자열 query에서 시작하는 편의 API
* `run(runcontext)` : 고급 사용자를 위한 명시적 API

---

## 사용 패턴

### 1) 초급: SequentialFlow로 구성하고 run_query로 실행

초급 사용자는 보통 “구성만 하고 실행”하면 됩니다.

```python
flow = SequentialFlow(steps=[retriever, builder, generator, validator])
out = flow.run_query("지난달 매출")
```

### 2) 고급: CustomFlow로 제어(while/if/policy)

정책/루프/재시도 같은 제어가 들어오면 `BaseFlow`를 직접 상속해 작성하는 것이 가장 깔끔합니다.

```python
class RetryFlow(BaseFlow):
    def run(self, run: RunContext) -> RunContext:
        while True:
            run = retriever(run)
            metrics = eval_retrieval(run)  # 순수 함수 가능
            action = policy(metrics)       # 순수 함수 가능
            if action == "retry":
                continue
            break

        run = generator(run)
        run = validator(run)
        return run
```

### 3) Sequential을 유지하면서 동적 파라미터가 필요하면 closure/partial

이건 “필수”가 아니라, **steps 배열을 유지하고 싶은 사람을 위한 옵션**입니다.

---

## Hook(Tracing)은 어디서 확인하나?

Flow도 hook을 받을 수 있습니다.

```python
from lang2sql.core.hooks import MemoryHook

hook = MemoryHook()
flow = SequentialFlow(steps=[...], hook=hook)

out = flow.run_query("지난달 매출")

for e in hook.events:
    print(e.name, e.phase, e.component, e.duration_ms, e.error)
```

운영에서는 `MemoryHook` 대신 로그/OTel/필터링 훅을 사용합니다.
관측성 제어는 **hook 구현체에서** 담당하고, Flow 코드는 비즈니스 로직에 집중하도록 분리합니다.

---

## (관련 개념) BaseFlow와 BaseComponent의 관계

* `BaseFlow`는 “어떻게 실행할지(제어/조립)”를 담당합니다.
* `BaseComponent`는 “한 단계에서 무엇을 할지(작업 단위)”를 담당합니다.

일반적으로:

* **Flow는 여러 Component를 호출**하거나,
* **SequentialFlow는 Component/함수를 steps로 받아 순차 실행**합니다.

즉, **Flow가 상위 레벨 오케스트레이션**, Component가 **재사용 가능한 부품**입니다.

---

## FAQ

### Q. BaseFlow가 필수인가?

A. Flow라는 개념은 사실상 필요하지만, **모든 사용자가 BaseFlow를 직접 상속할 필요는 없습니다.**

* 초급: `SequentialFlow`만 사용
* 고급: `BaseFlow`를 상속해서 제어를 직접 작성

### Q. Flow의 반환 타입은?

A. `run()`은 **반드시 `RunContext`를 반환**하는 것을 권장합니다.
(합성/디버깅/타입 안정성 측면에서 이득이 큽니다.)

---

