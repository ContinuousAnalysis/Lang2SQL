# Core Concepts

Lang2SQL은 “그래프 엔진/DSL”을 강제하지 않고, **순수 Python 코드로 파이프라인을 제어**하는 define-by-run 철학을 따릅니다.
대신, 파이프라인이 커져도 연결이 무너지지 않도록 **`RunContext`라는 최소 상태 컨테이너**를 중심으로 설계합니다.

---

## 1) Define-by-run: 제어는 Python으로

Lang2SQL에서 파이프라인 제어는 프레임워크가 아니라 **사용자 코드가 가집니다.**

* 분기: `if / match`
* 반복/재시도: `for / while`
* 조건부 실행: policy 기반 action
* 서브플로우: flow를 step처럼 호출

예시:

```python
def ret(run): ...
def ret_val(run): ...
def policy(metrics): ...
def gen(run): ...

run = RunContext("q")

while True:
    run = ret(run)
    metrics = ret_val(run)          # ✅ run 몰라도 되는 순수 함수 가능
    action = policy(metrics)        # ✅ run 몰라도 되는 순수 함수 가능
    if action == "retry":
        continue
    break

run = gen(run)
```

**핵심:** Lang2SQL은 위 패턴을 “프레임워크 문법”으로 바꾸지 않습니다.
그냥 Python으로 쓰되, 파이프라인 간 상태 전달을 안정적으로 하기 위해 `RunContext`를 사용합니다.

---

## 2) 왜 RunContext가 필요한가?

Text2SQL 파이프라인은 현실적으로 단계가 늘어납니다.

* retriever 1개가 아니라 10개, 100개가 될 수 있음
* 중간 산출물(선택된 테이블, 컨텍스트, 후보 SQL, 검증 결과, 점수/메트릭)이 늘어남
* loop/branch가 들어가면서 “어떤 단계에서 무엇이 생성되었는지” 추적이 어려워짐

이 상황에서 단계마다 함수 시그니처를 계속 바꾸면:

* `retriever(query, catalog) -> selected`
* `builder(query, selected) -> context`
* `generator(query, context) -> sql`
* `validator(sql) -> validation`

처럼 보이지만, 실제로는 **중간에 필요한 값이 계속 추가**되어 시그니처가 폭발합니다.

### RunContext는 “큰 그래프에서 연결 안정성”을 만든다

Lang2SQL은 각 step의 I/O를 **`RunContext -> RunContext`**로 고정합니다.

* step이 늘어나도 “연결 방식”이 바뀌지 않음
* 어떤 단계가 어떤 값을 추가해도, 다음 단계는 필요한 값을 `run`에서 읽으면 됨
* loop/branch/서브플로우에서도 동일한 규약 유지

그래서 문서에서 아래처럼 “개념적 함수형”으로 설명하더라도:

* retriever: (query, catalog) -> selected
* builder: (query, selected) -> context
* generator: (query, context) -> sql
* validator: (sql) -> validation

실제 구현은 **RunContext 내부 필드의 Read/Write 규약**으로 통일됩니다.

예:

* retriever: `run.query`, `run.schema_catalog` 읽고 → `run.schema_selected` 씀
* builder: `run.query`, `run.schema_selected` 읽고 → `run.schema_context` 씀
* generator: `run.query`, `run.schema_context` 읽고 → `run.sql` 씀
* validator: `run.sql` 읽고 → `run.validation` 씀

### “쿼리가 바뀌면?”도 제어 가능

`RunContext`는 mutable state carrier이므로, 루프 중간에 쿼리를 업데이트해도 됩니다.

```python
run.query = rewritten_query
run = ret(run)  # 업데이트된 query로 재검색
```

---

## 3) `run(runcontext)` vs `run_query(query)`

두 API의 관계는 단순합니다.

### `run(run: RunContext) -> RunContext`

* **명시적 엔트리포인트**
* 고급 제어(루프/분기/정책)나 서브플로우 합성에서 자연스럽습니다.

```python
run = RunContext(query="지난달 매출")
out = flow.run(run)
```

### `run_query(query: str) -> RunContext`

* **편의(sugar) 엔트리포인트**
* 초급/데모/퀵스타트에서 `RunContext`를 몰라도 실행 가능하게 합니다.
* 내부적으로는 보통 아래와 동치입니다:

```python
out = flow.run(RunContext(query=query))
```

즉,

```python
out1 = flow.run_query("지난달 매출")
out2 = flow.run(RunContext(query="지난달 매출"))
```

은 **같은 기능**을 제공합니다. 차이는 **입력 형태(문자열 vs RunContext)** 뿐입니다.

---

## 권장 규약 요약

* **제어는 Python으로 한다** (define-by-run)
* **상태 전달은 RunContext로 고정한다** (`RunContext -> RunContext`)
* `run_query()`는 **초급/데모용 편의 API**, `run()`은 **명시적/고급 제어용 API**
* policy/eval처럼 RunContext가 필요 없는 로직은 **순수 함수로 둬도 된다** (필요하면 run에서 읽거나 metadata로 남기는 건 선택)

---
