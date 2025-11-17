# sidebar_components

사이드바 UI 컴포넌트 모듈. Streamlit 애플리케이션의 사이드바에서 사용되는 설정 선택 및 관리 컴포넌트들을 제공합니다.

## 디렉토리 구조

```
sidebar_components/
├── __init__.py
├── chatbot_session_controller.py
├── data_source_selector.py
├── db_selector.py
├── embedding_selector.py
└── llm_selector.py
```

## 파일 설명

### `__init__.py`

모든 사이드바 컴포넌트 함수들을 모듈에서 export합니다.

**Export되는 함수:**
- `render_sidebar_data_source_selector`: 데이터 소스 선택기 렌더링
- `render_sidebar_llm_selector`: LLM 선택기 렌더링
- `render_sidebar_embedding_selector`: Embeddings 선택기 렌더링
- `render_sidebar_db_selector`: DB 연결 선택기 렌더링
- `render_sidebar_chatbot_session_controller`: ChatBot 세션 컨트롤러 렌더링

**사용 예시:**
```python
from interface.app_pages.sidebar_components import (
    render_sidebar_data_source_selector,
    render_sidebar_llm_selector,
    render_sidebar_embedding_selector,
    render_sidebar_db_selector,
    render_sidebar_chatbot_session_controller,
)
```

---

### `chatbot_session_controller.py`

ChatBot 세션 관리 및 대화 기록 표시를 위한 사이드바 컴포넌트입니다.

**주요 기능:**
- 세션 ID 자동 생성 및 관리 (`chatbot_thread_id`)
- 새 세션 시작 버튼
- 대화 기록 표시 (JSON 형식)
- 최근 메시지 미리보기 (최근 3개)

**함수:**
```python
def render_sidebar_chatbot_session_controller() -> str
```

**반환값:**
- `str`: 현재 thread_id

**사용 예시:**
```python
from interface.app_pages.sidebar_components import render_sidebar_chatbot_session_controller

thread_id = render_sidebar_chatbot_session_controller()
```

**의존성:**
- `streamlit`: UI 렌더링
- `uuid`: 세션 ID 생성
- `st.session_state`: 세션 상태 관리
  - `chatbot_thread_id`: 현재 세션 ID
  - `chatbot_messages`: 대화 기록 리스트

**사용처:**
- `/home/dwlee/Lang2SQL/interface/app_pages/chatbot.py` (line 112)

---

### `data_source_selector.py`

데이터 소스 선택 컴포넌트입니다. DataHub 또는 VectorDB 중 하나를 선택하고 설정을 적용할 수 있습니다.

**주요 기능:**
- DataHub/VectorDB 모드 선택 (라디오 버튼)
- DataHub 인스턴스 선택 및 적용
- VectorDB 인스턴스 선택 및 적용
- FAISS 경로 자동 적용 (DataHub 선택 시)

**함수:**
```python
def render_sidebar_data_source_selector(config=None) -> None
```

**매개변수:**
- `config` (optional): 설정 객체. None인 경우 내부에서 `load_config()`로 로드합니다.

**사용 예시:**
```python
from interface.app_pages.sidebar_components import render_sidebar_data_source_selector
from interface.core.config import load_config

config = load_config()
render_sidebar_data_source_selector(config)
```

**의존성:**
- `streamlit`: UI 렌더링
- `interface.core.config`:
  - `load_config()`: 설정 로드
  - `get_data_sources_registry()`: 데이터 소스 레지스트리 조회
  - `update_datahub_server()`: DataHub 서버 설정 업데이트
  - `update_vectordb_settings()`: VectorDB 설정 업데이트
  - `update_data_source_mode()`: 데이터 소스 모드 업데이트

**사용처:**
- `/home/dwlee/Lang2SQL/interface/app_pages/chatbot.py` (line 99)
- `/home/dwlee/Lang2SQL/interface/app_pages/lang2sql.py` (line 50)

---

### `db_selector.py`

데이터베이스 연결 프로파일 선택 컴포넌트입니다.

**주요 기능:**
- 등록된 DB 프로파일 목록 표시
- 프로파일 선택 및 적용
- 세션 또는 환경 변수의 DB_TYPE과 일치하는 프로파일 자동 선택

**함수:**
```python
def render_sidebar_db_selector() -> None
```

**사용 예시:**
```python
from interface.app_pages.sidebar_components import render_sidebar_db_selector

render_sidebar_db_selector()
```

**의존성:**
- `streamlit`: UI 렌더링
- `os`: 환경 변수 조회
- `interface.core.config`:
  - `get_db_connections_registry()`: DB 연결 레지스트리 조회
  - `update_db_settings()`: DB 설정 업데이트
- `st.session_state.get("DB_TYPE")`: 세션의 DB 타입 확인
- `os.getenv("DB_TYPE")`: 환경 변수에서 DB 타입 확인

**사용처:**
- `/home/dwlee/Lang2SQL/interface/app_pages/chatbot.py` (line 105)
- `/home/dwlee/Lang2SQL/interface/app_pages/lang2sql.py` (line 56)

---

### `embedding_selector.py`

Embeddings 프로파일 선택 컴포넌트입니다.

**주요 기능:**
- 등록된 Embeddings 프로파일 목록 표시
- 프로파일 선택 및 적용
- 프로파일이 없는 경우 공급자 직접 선택 (fallback 모드)
- 지원 공급자: openai, azure, bedrock, gemini, ollama, huggingface

**함수:**
```python
def render_sidebar_embedding_selector() -> None
```

**사용 예시:**
```python
from interface.app_pages.sidebar_components import render_sidebar_embedding_selector

render_sidebar_embedding_selector()
```

**의존성:**
- `streamlit`: UI 렌더링
- `os`: 환경 변수 조회
- `interface.core.config`:
  - `get_embedding_registry()`: Embeddings 레지스트리 조회
  - `update_embedding_settings()`: Embeddings 설정 업데이트
- `st.session_state.get("EMBEDDING_PROVIDER")`: 세션의 Embeddings 공급자 확인
- `os.getenv("EMBEDDING_PROVIDER")`: 환경 변수에서 Embeddings 공급자 확인

**사용처:**
- `/home/dwlee/Lang2SQL/interface/app_pages/chatbot.py` (line 103)
- `/home/dwlee/Lang2SQL/interface/app_pages/lang2sql.py` (line 54)

---

### `llm_selector.py`

LLM 프로파일 선택 컴포넌트입니다.

**주요 기능:**
- 등록된 LLM 프로파일 목록 표시
- 프로파일 선택 및 적용
- 프로파일이 없는 경우 공급자 직접 선택 (fallback 모드)
- 지원 공급자: openai, azure, bedrock, gemini, ollama, huggingface

**함수:**
```python
def render_sidebar_llm_selector() -> None
```

**사용 예시:**
```python
from interface.app_pages.sidebar_components import render_sidebar_llm_selector

render_sidebar_llm_selector()
```

**의존성:**
- `streamlit`: UI 렌더링
- `os`: 환경 변수 조회
- `interface.core.config`:
  - `get_llm_registry()`: LLM 레지스트리 조회
  - `update_llm_settings()`: LLM 설정 업데이트
- `st.session_state.get("LLM_PROVIDER")`: 세션의 LLM 공급자 확인
- `os.getenv("LLM_PROVIDER")`: 환경 변수에서 LLM 공급자 확인

**사용처:**
- `/home/dwlee/Lang2SQL/interface/app_pages/chatbot.py` (line 101)
- `/home/dwlee/Lang2SQL/interface/app_pages/lang2sql.py` (line 52)

---

## 전체 사용 예시

### chatbot.py에서의 사용

```python
from interface.app_pages.sidebar_components import (
    render_sidebar_data_source_selector,
    render_sidebar_llm_selector,
    render_sidebar_embedding_selector,
    render_sidebar_db_selector,
    render_sidebar_chatbot_session_controller,
)
from interface.core.config import load_config

config = load_config()

# 사이드바 UI 구성
render_sidebar_data_source_selector(config)
st.sidebar.divider()
render_sidebar_llm_selector()
st.sidebar.divider()
render_sidebar_embedding_selector()
st.sidebar.divider()
render_sidebar_db_selector()
st.sidebar.divider()

# ChatBot 전용 설정
with st.sidebar:
    st.markdown("### 🤖 ChatBot 설정")
    st.divider()
    thread_id = render_sidebar_chatbot_session_controller()
```

### lang2sql.py에서의 사용

```python
from interface.app_pages.sidebar_components import (
    render_sidebar_data_source_selector,
    render_sidebar_llm_selector,
    render_sidebar_embedding_selector,
    render_sidebar_db_selector,
)
from interface.core.config import load_config

config = load_config()

render_sidebar_data_source_selector(config)
st.sidebar.divider()
render_sidebar_llm_selector()
st.sidebar.divider()
render_sidebar_embedding_selector()
st.sidebar.divider()
render_sidebar_db_selector()
st.sidebar.divider()
```

## 공통 패턴

모든 컴포넌트는 다음과 같은 공통 패턴을 따릅니다:

1. **레지스트리 기반**: 각 컴포넌트는 해당 설정의 레지스트리(`get_*_registry()`)에서 프로파일/인스턴스 목록을 가져옵니다.
2. **Fallback 지원**: 프로파일이 없는 경우 기본 공급자 선택 옵션을 제공합니다.
3. **세션/환경 변수 통합**: 현재 세션 상태 또는 환경 변수와 일치하는 항목을 자동으로 선택합니다.
4. **설정 업데이트**: 선택한 항목을 적용하면 `update_*_settings()` 함수를 통해 설정을 업데이트합니다.
5. **에러 처리**: 적용 실패 시 `st.sidebar.error()`로 에러 메시지를 표시합니다.

