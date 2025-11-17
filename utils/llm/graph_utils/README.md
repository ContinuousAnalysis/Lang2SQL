# graph_utils

이 모듈은 **LangGraph workflow**를 위한 그래프 유틸리티들을 제공합니다. Lang2SQL 프로젝트에서 자연어 질문을 SQL 쿼리로 변환하는 워크플로우를 LangGraph를 사용하여 구성합니다.

## 디렉토리 구조

```
graph_utils/
├── __init__.py
├── base.py
├── basic_graph.py
├── enriched_graph.py
├── profile_utils.py
└── README.md
```

## 파일 설명

### `__init__.py`
그래프 관련 유틸리티 모듈의 공개 인터페이스를 정의합니다.

**주요 사용:**
- **상태 및 노드 식별자:**
  - `QueryMakerState`: 그래프의 상태 타입 정의
  - `GET_TABLE_INFO`, `QUERY_MAKER`, `PROFILE_EXTRACTION`, `CONTEXT_ENRICHMENT`: 노드 식별자 상수

- **노드 함수들:**
  - `get_table_info_node`: 테이블 정보 검색 노드
  - `query_maker_node`: SQL 쿼리 생성 노드
  - `profile_extraction_node`: 질문 프로파일 추출 노드
  - `context_enrichment_node`: 컨텍스트 보강 노드

- **그래프 빌더들:**
  - `basic_builder`: 기본 워크플로우 그래프 빌더
  - `enriched_builder`: 확장된 워크플로우 그래프 빌더

### `base.py`
LangGraph 워크플로우의 핵심 노드 함수들과 상태 정의를 포함합니다.

**주요 내용:**
- **상태 타입 (`QueryMakerState`):** TypedDict를 사용하여 그래프 상태 구조를 정의
  - `messages`: LLM 메시지 리스트
  - `user_database_env`: 사용자 데이터베이스 환경
  - `searched_tables`: 검색된 테이블 정보
  - `question_profile`: 질문 프로파일 정보
  - `generated_query`: 생성된 SQL 쿼리
  - 기타 워크플로우에 필요한 상태 정보

- **노드 식별자 상수:**
  - `QUESTION_GATE`, `EVALUATE_DOCUMENT_SUITABILITY`, `GET_TABLE_INFO`, `TOOL`, `TABLE_FILTER`, `QUERY_MAKER`, `PROFILE_EXTRACTION`, `CONTEXT_ENRICHMENT`

- **노드 함수들:**
  - `question_gate_node`: 사용자 질문이 SQL로 답변 가능한지 판별하는 게이트 노드
  - `get_table_info_node`: 벡터 검색을 통해 관련 테이블 정보를 가져오는 노드
  - `document_suitability_node`: 검색된 테이블들의 문서 적합성 점수를 계산하는 노드
  - `profile_extraction_node`: 자연어 쿼리로부터 질문 유형(시계열, 집계, 필터 등)을 추출하는 노드
  - `context_enrichment_node`: 질문과 관련된 메타데이터를 기반으로 질문을 풍부하게 만드는 노드
  - `query_maker_node`: 최종 SQL 쿼리를 생성하는 노드

### `basic_graph.py`
기본 워크플로우를 위한 StateGraph 구성을 정의합니다.

**워크플로우 순서:**
```
QUESTION_GATE → GET_TABLE_INFO → EVALUATE_DOCUMENT_SUITABILITY → QUERY_MAKER → END
```

**주요 내용:**
- `StateGraph`를 사용하여 기본 워크플로우 그래프 생성
- `builder` 객체를 export하여 다른 모듈에서 사용 가능
- 조건부 라우팅(`add_conditional_edges`)을 통해 게이트 노드 이후 흐름 제어

### `enriched_graph.py`
기본 워크플로우에 프로파일 추출과 컨텍스트 보강 단계를 추가한 확장된 그래프입니다.

**워크플로우 순서:**
```
QUESTION_GATE → GET_TABLE_INFO → EVALUATE_DOCUMENT_SUITABILITY → 
PROFILE_EXTRACTION → CONTEXT_ENRICHMENT → QUERY_MAKER → END
```

**주요 내용:**
- `basic_graph`와 동일한 구조이지만 `PROFILE_EXTRACTION`과 `CONTEXT_ENRICHMENT` 노드가 추가됨
- 더 정교한 질문 분석과 컨텍스트 보강을 통해 더 나은 SQL 쿼리 생성이 가능

### `profile_utils.py`
질문 프로파일 객체를 텍스트로 변환하는 유틸리티 함수를 제공합니다.

**주요 함수:**
- `profile_to_text(profile_obj) -> str`: 질문 프로파일 객체를 읽기 쉬운 텍스트 형태로 변환
  - 시계열 분석 필요 여부
  - 집계 함수 필요 여부
  - WHERE 조건 필요 여부
  - GROUP BY 필요 여부
  - 정렬/순위 필요 여부
  - 기간 비교 필요 여부
  - 의도 유형 정보

## 사용 방법

### 1. `engine/query_executor.py`에서의 사용

기본 또는 확장된 그래프 빌더를 선택하여 쿼리를 실행합니다:

```python
from utils.llm.graph_utils.basic_graph import builder as basic_builder
from utils.llm.graph_utils.enriched_graph import builder as enriched_builder

# 그래프 선택
if use_enriched_graph:
    graph_builder = enriched_builder
else:
    graph_builder = basic_builder

# 그래프 컴파일 및 실행
graph = graph_builder.compile()
result = graph.invoke({
    "messages": [HumanMessage(content=query)],
    "user_database_env": database_env,
    # ... 기타 상태 정보
})
```

**사용 위치:** `/home/dwlee/Lang2SQL/engine/query_executor.py`의 `execute_query()` 함수

### 2. `interface/core/session_utils.py`에서의 사용

Streamlit 세션 상태에서 그래프 빌더를 동적으로 초기화합니다:

```python
def init_graph(use_enriched: bool) -> str:
    builder_module = (
        "utils.llm.graph_utils.enriched_graph"
        if use_enriched
        else "utils.llm.graph_utils.basic_graph"
    )
    builder = __import__(builder_module, fromlist=["builder"]).builder
    st.session_state["graph"] = builder.compile()
    return "확장된" if use_enriched else "기본"
```

**사용 위치:** `/home/dwlee/Lang2SQL/interface/core/session_utils.py`의 `init_graph()` 함수

### 3. `interface/app_pages/graph_builder.py`에서의 사용

Streamlit 인터페이스에서 커스텀 그래프를 구성할 때 개별 노드 함수들을 사용합니다:

```python
from utils.llm.graph_utils.base import (
    CONTEXT_ENRICHMENT,
    GET_TABLE_INFO,
    PROFILE_EXTRACTION,
    QUERY_MAKER,
    QueryMakerState,
    context_enrichment_node,
    get_table_info_node,
    profile_extraction_node,
    query_maker_node,
)

# 커스텀 시퀀스에 따라 노드 등록
builder = StateGraph(QueryMakerState)
for node_id in sequence:
    if node_id == GET_TABLE_INFO:
        builder.add_node(GET_TABLE_INFO, get_table_info_node)
    elif node_id == PROFILE_EXTRACTION:
        builder.add_node(PROFILE_EXTRACTION, profile_extraction_node)
    # ... 기타 노드들
```

**사용 위치:** `/home/dwlee/Lang2SQL/interface/app_pages/graph_builder.py`의 `build_state_graph()` 함수

## 워크플로우 개요

이 모듈은 **LangGraph**를 사용하여 자연어 질문을 SQL 쿼리로 변환하는 워크플로우를 구현합니다:

1. **QUESTION_GATE**: 질문이 SQL로 답변 가능한지 판별
2. **GET_TABLE_INFO**: 벡터 검색을 통해 관련 테이블 정보 검색
3. **EVALUATE_DOCUMENT_SUITABILITY**: 검색된 테이블들의 적합성 평가
4. **PROFILE_EXTRACTION** (확장 그래프만): 질문의 특성 추출 (시계열, 집계 등)
5. **CONTEXT_ENRICHMENT** (확장 그래프만): 질문을 컨텍스트 정보로 보강
6. **QUERY_MAKER**: 최종 SQL 쿼리 생성

각 노드는 `QueryMakerState`를 입력으로 받아 상태를 업데이트하고 반환합니다.

