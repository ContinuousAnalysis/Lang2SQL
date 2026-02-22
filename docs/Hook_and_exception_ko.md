# Hooks (Tracing)

Lang2SQL의 hooks 시스템은 **그래프 엔진 없이도 관측성(observability)을 제공**하기 위한 최소 레이어입니다.
Flow/Component 실행 과정에서 이벤트를 발행하고, 사용자는 hook 구현체로 이를 수집/출력/전송할 수 있습니다.

핵심 컨셉은 단 하나입니다:

> **“실행 중 무슨 일이 일어났는지(Event)를 hook이 받는다.”**

---

## Event

`Event`는 Flow/Component 실행 중 발생한 “관측 단위”입니다.

```py
@dataclass
class Event:
    name: str                 # e.g., "component.run" / "flow.run"
    component: str            # e.g., "KeywordTableRetriever" / "SequentialFlow"
    phase: Literal["start", "end", "error"]
    ts: float                 # unix timestamp
    duration_ms: Optional[float] = None

    input_summary: Optional[str] = None
    output_summary: Optional[str] = None
    error: Optional[str] = None

    data: dict[str, Any] = field(default_factory=dict)
```

### 필드 의미

* `name`

  * 이벤트 종류를 나타내는 문자열
  * 예: `"component.run"`, `"flow.run"`
* `component`

  * 이벤트를 발생시킨 실행 단위 이름
  * 예: `"KeywordTableRetriever"`, `"SequentialFlow"`
* `phase`

  * `"start" | "end" | "error"`
* `ts`

  * 이벤트 발생 시간(Unix timestamp)
* `duration_ms`

  * `end/error`에서만 주로 채움(실행 시간)
* `input_summary`, `output_summary`

  * 디버깅을 위한 “사람이 읽기 쉬운” 요약 문자열
* `error`

  * 실패 시 오류 요약 문자열
* `data`

  * UI/필터링/테스트/추가 메타를 위한 구조화 payload
  * 기본은 빈 dict이며, 필요할 때만 채우는 것을 권장합니다.

---

## TraceHook

`TraceHook`은 이벤트를 받는 인터페이스입니다.

```py
class TraceHook(Protocol):
    def on_event(self, event: Event) -> None: ...
```

* Lang2SQL의 Flow/Component는 실행 시점에 `hook.on_event(Event(...))` 형태로 이벤트를 발행합니다.
* hook은 **옵션**이며, 없으면 `NullHook`이 사용됩니다.

---

## 기본 Hook 구현체

### NullHook

```py
class NullHook:
    def on_event(self, event: Event) -> None:
        return
```

* 기본값
* 아무 것도 하지 않습니다.
* hook 비용을 없애고 싶을 때 항상 안전한 기본 구현입니다.

### MemoryHook

```py
class MemoryHook:
    def __init__(self) -> None:
        self.events: list[Event] = []

    def on_event(self, event: Event) -> None:
        self.events.append(event)

    def clear(self) -> None:
        self.events.clear()

    def snapshot(self) -> list[Event]:
        return list(self.events)
```

* 이벤트를 메모리에 누적합니다.
* 테스트/디버깅에 가장 유용합니다.

#### MemoryHook 사용 예시

```py
from lang2sql.core.hooks import MemoryHook
from lang2sql.flows.baseline import BaselineFlow

hook = MemoryHook()
flow = BaselineFlow(steps=[...], hook=hook)

out = flow.run_query("지난달 매출")

for e in hook.events:
    print(e.name, e.phase, e.component, e.duration_ms, e.error)
```

#### clear()를 유저가 직접 호출해야 하나?

* 보통은 **테스트에서만** `clear()`가 필요합니다. (케이스 간 이벤트 섞임 방지)
* 일반 사용자는 보통 “요청 1회 → hook 1개 생성” 패턴으로 충분합니다.

예:

```py
hook = MemoryHook()
out = flow.run_query("q")   # 여기서만 쓰고 끝
events = hook.snapshot()
```

---

## 유틸 함수

### now()

```py
def now() -> float:
    return time.time()
```

* timestamp 생성에 사용됩니다.

### ms()

```py
def ms(start: float, end: float) -> float:
    return (end - start) * 1000.0
```

* duration(ms) 계산에 사용됩니다.

### summarize()

```py
def summarize(x: Any, max_len: int = 240) -> str:
    ...
```

* repr(x)를 기반으로 요약 문자열을 만들고 길이를 제한합니다.
* 이벤트의 `input_summary/output_summary`에 사용됩니다.

---

## 운영(Production)에서는 어떻게 쓰나?

MemoryHook은 테스트용입니다. 운영에서는 보통 다음 형태로 확장합니다.

* `LoggingHook`: JSON 로그로 남기기
* `OTelHook`: OpenTelemetry span으로 전송
* `FilteringHook`: 특정 component만 샘플링/필터링

관측성 제어는 **hook 구현체에서** 하고, Flow/Component 로직은 비즈니스에 집중하는 것이 기본 철학입니다.

---

# Exceptions

Lang2SQL 예외 시스템은 두 목표를 가집니다.

1. **도메인 에러는 도메인 타입으로 유지**한다.
2. 외부/일반 예외는 “어디서 터졌는지”가 보이도록 **표준 래핑**한다.

---

## Lang2SQLError (Base)

```py
class Lang2SQLError(Exception):
    """Base error for lang2sql."""
```

* Lang2SQL에서 발생하는 모든 도메인 예외의 베이스입니다.
* `BaseComponent` / `BaseFlow`는 일반적으로 **Lang2SQLError는 그대로 다시 raise**합니다.

---

## IntegrationMissingError

```py
class IntegrationMissingError(Lang2SQLError):
    def __init__(self, integration: str, extra: str | None = None, hint: str | None = None):
        ...
```

### 언제 발생?

* 선택적 의존성(optional integration)이 필요한데 설치되어 있지 않을 때

예:

* `faiss` retriever를 쓰는데 `faiss`가 설치되어 있지 않음

### 메시지 특징

* `extra`가 있으면 설치 힌트를 포함합니다.

예 메시지:

* `Missing optional integration: faiss. Install with: pip install 'lang2sql[faiss]'`

---

## ValidationError

```py
class ValidationError(Lang2SQLError):
    pass
```

### 언제 발생?

* SQL 검증 실패, 정책상 금지 쿼리, 스키마 불일치 등
* “유저 입력/생성 결과가 유효하지 않다”에 해당하는 에러를 담는 대표 도메인 예외

---

## ContractError

```py
class ContractError(Lang2SQLError):
    """Raised when a component violates a required call/return contract."""
    pass
```

### 언제 발생?

* Lang2SQL이 요구하는 호출/반환 계약을 위반했을 때
* 예: `RunContext -> RunContext` 계약인데 `None` 또는 `int`를 반환

이 에러는 “사용자 코드 버그를 빨리 발견(fail-fast)”하기 위한 타입입니다.

---

## ComponentError

```py
class ComponentError(Lang2SQLError):
    def __init__(self, component: str, message: str, *, cause: Exception | None = None):
        self.component = component
        self.cause = cause
        super().__init__(f"[{component}] {message}")
```

### 목적

* “일반 예외(ValueError, KeyError 등)”를 도메인 레이어로 끌어올 때 사용합니다.
* 어떤 컴포넌트에서 터졌는지 식별 가능하게 만듭니다.

### cause

* 원본 예외를 보존합니다.
* 테스트/디버깅에서 error chain을 확인할 수 있습니다.

---

## 예외가 Flow/Component에서 어떻게 처리되나?

(현재 BaseComponent 설계 기준)

* `Lang2SQLError` 계열

  * 그대로 이벤트에 기록하고 그대로 raise
* 그 외 모든 예외

  * 이벤트에 기록하고 `ComponentError(..., cause=e)`로 래핑하여 raise

즉:

* **도메인 예외는 “정상적인 실패”로 취급**
* **일반 예외는 “버그/예상 밖 실패”로 표준화**

---

## 권장 사용 가이드

* “사용자 입력/정책/검증 실패”는 `ValidationError`
* “의존성 설치 문제”는 `IntegrationMissingError`
* “계약 위반(반환 타입/호출 규약)”은 `ContractError`
* “외부 라이브러리/예상 밖 예외”는 `ComponentError`로 래핑되어 올라오는 것을 기본으로 합니다.

---
