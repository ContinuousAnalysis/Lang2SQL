# engine 모듈

Lang2SQL 쿼리 실행을 위한 공용 모듈입니다.

이 모듈은 CLI와 Streamlit 인터페이스에서 공통으로 사용할 수 있는 쿼리 실행 함수를 제공합니다.

## 디렉토리 구조

```
engine/
├── __init__.py                      # 패키지 초기화 모듈
├── query_executor.py                 # 쿼리 실행 공용 함수
└── README.md                         # 이 파일
```

## 모듈 개요

### `__init__.py`
- **위치**: `engine/__init__.py`
- **설명**: Lang2SQL Data Processing 진입점 패키지
- **내용**: 패키지 초기화 모듈

### `query_executor.py`
- **위치**: `engine/query_executor.py`
- **설명**: Lang2SQL 쿼리 실행을 위한 공용 모듈
- **주요 기능**:
  - `execute_query()`: 자연어 쿼리를 SQL로 변환하고 실행 결과를 반환
  - `extract_sql_from_result()`: Lang2SQL 실행 결과에서 SQL 쿼리 추출

#### 주요 함수

##### `execute_query()`
자연어 쿼리를 SQL로 변환하고 실행 결과를 반환하는 공용 함수입니다.

**매개변수:**
- `query` (str): 사용자가 입력한 자연어 기반 질문
- `database_env` (str): 사용할 데이터베이스 환경 이름 또는 키 (예: "dev", "prod")
- `retriever_name` (str, optional): 테이블 검색기 이름. 기본값은 "기본"
- `top_n` (int, optional): 검색된 상위 테이블 수 제한. 기본값은 5
- `device` (str, optional): LLM 실행에 사용할 디바이스 ("cpu" 또는 "cuda"). 기본값은 "cpu"
- `use_enriched_graph` (bool, optional): 확장된 그래프 사용 여부. 기본값은 False
- `session_state` (Optional[Union[Dict[str, Any], Any]], optional): Streamlit 세션 상태 (Streamlit에서만 사용)

**반환값:**
- `Dict[str, Any]`: 다음 정보를 포함한 Lang2SQL 실행 결과 딕셔너리:
  - `"generated_query"`: 생성된 SQL 쿼리 (`AIMessage`)
  - `"messages"`: 전체 LLM 응답 메시지 목록
  - `"searched_tables"`: 참조된 테이블 목록 등 추가 정보

**동작 방식:**
1. 사용자가 지정한 옵션에 따라 기본 그래프 또는 확장 그래프를 선택
2. Streamlit 환경에서는 세션 상태에서 그래프 재사용, CLI 환경에서는 매번 새로운 그래프 컴파일
3. 선택된 그래프를 컴파일하고 invoke하여 결과 반환

**사용 예제:**
```python
from engine.query_executor import execute_query

# CLI 환경에서 사용
result = execute_query(
    query="고객 데이터를 기반으로 유니크한 유저 수를 카운트하는 쿼리",
    database_env="clickhouse",
    retriever_name="기본",
    top_n=5,
    device="cpu",
    use_enriched_graph=False
)

# Streamlit 환경에서 사용
result = execute_query(
    query="고객 데이터를 기반으로 유니크한 유저 수를 카운트하는 쿼리",
    database_env="clickhouse",
    retriever_name="기본",
    top_n=5,
    device="cpu",
    use_enriched_graph=False,
    session_state=st.session_state  # Streamlit 세션 상태 전달
)
```

##### `extract_sql_from_result()`
Lang2SQL 실행 결과에서 SQL 쿼리를 추출합니다.

**매개변수:**
- `res` (Dict[str, Any]): `execute_query()` 함수의 반환 결과

**반환값:**
- `Optional[str]`: 추출된 SQL 쿼리 문자열. 추출 실패 시 None

**동작 방식:**
1. `generated_query` 필드에서 쿼리 메시지 추출
2. `LLMResponseParser.extract_sql()`을 사용하여 SQL 쿼리 문자열 추출
3. 추출 실패 시 None 반환

**사용 예제:**
```python
from engine.query_executor import execute_query, extract_sql_from_result

result = execute_query(
    query="고객 데이터를 기반으로 유니크한 유저 수를 카운트하는 쿼리",
    database_env="clickhouse"
)

sql = extract_sql_from_result(result)
if sql:
    print(sql)
```

## 의존성

### 내부 모듈
- `utils.llm.graph_utils.basic_graph.builder`: 기본 그래프 빌더
- `utils.llm.graph_utils.enriched_graph.builder`: 확장 그래프 빌더
- `utils.llm.llm_response_parser.LLMResponseParser`: LLM 응답 파서

### 외부 라이브러리
- `langchain_core.messages.HumanMessage`: LangChain 메시지 클래스

## 사용 위치

### 1. CLI 명령어 (`cli/commands/quary.py`)
CLI 환경에서 `query` 명령어 실행 시 사용됩니다.

```python
from engine.query_executor import execute_query, extract_sql_from_result

# CLI 명령어에서 사용
res = execute_query(
    query=question,
    database_env=database_env,
    retriever_name=retriever_name,
    top_n=top_n,
    device=device,
    use_enriched_graph=use_enriched_graph,
)

sql = extract_sql_from_result(res)
```

### 2. Streamlit 인터페이스 (`interface/core/lang2sql_runner.py`)
Streamlit 인터페이스에서 Lang2SQL 실행을 위해 사용됩니다.

```python
from engine.query_executor import execute_query as execute_query_common

# Streamlit 러너에서 사용
def run_lang2sql(query, database_env, retriever_name, top_n, device):
    return execute_query_common(
        query=query,
        database_env=database_env,
        retriever_name=retriever_name,
        top_n=top_n,
        device=device,
    )
```

### 3. Streamlit 메인 페이지 (`interface/app_pages/lang2sql.py`)
Streamlit 메인 페이지에서 `lang2sql_runner.run_lang2sql()`을 호출하여 사용됩니다.

```python
from interface.core.lang2sql_runner import run_lang2sql

# 메인 페이지에서 사용
if st.button("쿼리 실행"):
    res = run_lang2sql(
        query=user_query,
        database_env=user_database_env,
        retriever_name=user_retriever,
        top_n=user_top_n,
        device=device,
    )
    display_result(res=res)
```

## 워크플로우

### 기본 워크플로우
1. 사용자가 자연어 질문 입력
2. `execute_query()` 호출
3. 기본 그래프 빌더 선택 및 컴파일
4. 그래프 실행하여 SQL 쿼리 생성
5. 결과 딕셔너리 반환

### 확장 워크플로우 (프로파일 추출 + 컨텍스트 보강)
1. 사용자가 자연어 질문 입력
2. `execute_query(use_enriched_graph=True)` 호출
3. 확장 그래프 빌더 선택 및 컴파일
4. 그래프 실행하여 SQL 쿼리 생성
5. 결과 딕셔너리 반환

## 환경별 동작

### CLI 환경
- 세션 상태 없이 매번 새로운 그래프 컴파일
- 중간 결과 저장/재사용 불가

### Streamlit 환경
- 세션 상태를 통해 그래프 재사용 가능
- 중간 결과 저장/재사용 가능
- 다이얼렉트 정보 주입 지원

## 로깅

이 모듈은 `logging` 모듈을 사용하여 로그를 기록합니다:
- 처리 중인 쿼리 로그
- 사용 중인 그래프 유형 로그
- SQL 추출 실패 시 에러 로그

## 주의사항

1. `session_state` 파라미터는 Streamlit 환경에서만 유효합니다
2. `use_enriched_graph=True`로 설정하면 더 많은 리소스가 소모될 수 있습니다
3. `database_env`는 유효한 데이터베이스 환경 이름이어야 합니다
4. 그래프 컴파일은 처음 실행 시 시간이 걸릴 수 있습니다

