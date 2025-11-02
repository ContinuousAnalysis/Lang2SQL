# settings_sections

설정 페이지의 각 섹션을 렌더링하는 모듈들입니다.

## 디렉토리 구조

```
settings_sections/
├── __init__.py
├── data_source_section.py
├── db_section.py
└── llm_section.py
```

## 파일 목록 및 설명

### `__init__.py`

네임스페이스 패키지 초기화 파일로, 패키지에서 export되는 모듈 목록을 정의합니다.

**내보내는 모듈:**
- `data_source_section`
- `llm_section`
- `db_section`

### `data_source_section.py`

데이터 소스 설정을 관리하는 UI 섹션을 제공합니다.

**주요 기능:**
- DataHub 또는 VectorDB 중 하나를 선택하여 데이터 소스 모드 설정
- DataHub 서버 관리:
  - 등록된 DataHub 목록 조회 및 표시
  - 새로운 DataHub 추가 (이름, URL, FAISS 저장 경로, 메모)
  - 기존 DataHub 편집 및 삭제
  - GMS 서버 헬스 체크 기능
- VectorDB 관리:
  - 등록된 VectorDB 목록 조회 및 표시 (FAISS, pgvector 지원)
  - 새로운 VectorDB 추가 (이름, 타입, 위치, 컬렉션 접두사, 메모)
  - 기존 VectorDB 편집 및 삭제
  - 설정 검증 기능

**주요 함수:**
- `render_data_source_section(config: Config | None = None) -> None`
  - 데이터 소스 설정 섹션을 Streamlit UI로 렌더링
  - `config` 파라미터가 없으면 내부에서 `load_config()`를 호출하여 로드

**의존성:**
- `interface.core.config`: Config 관리, 데이터 소스 레지스트리 조작
- `infra.monitoring.check_server.CheckServer`: GMS 서버 헬스 체크

**상태 표시:**
- 현재 선택된 데이터 소스 모드에 따라 상태 배너 표시
- DataHub: 헬스 체크 결과에 따른 성공/경고/정보 메시지
- VectorDB: 설정 완전성에 따른 성공/경고 메시지

### `db_section.py`

데이터베이스 연결 설정을 관리하는 UI 섹션을 제공합니다.

**주요 기능:**
- 다양한 DB 타입 지원:
  - PostgreSQL, MySQL, MariaDB, Oracle, ClickHouse
  - DuckDB, SQLite
  - Databricks, Snowflake, Trino
- DB 프로파일 관리:
  - 등록된 DB 프로파일 목록 조회 및 표시
  - 새로운 DB 프로파일 추가
  - 기존 DB 프로파일 편집 및 삭제
- DB 타입별 필드 동적 처리:
  - 기본 필드: Host, Port, User, Database (또는 Path for DuckDB/SQLite)
  - 추가 필드: Oracle(Service Name), Databricks(HTTP Path, Catalog, Schema), Snowflake(Account, Warehouse, Schema), Trino(HTTP Scheme, Catalog, Schema)
  - 비밀 필드: Password 또는 Access Token (타입별 상이)
- 환경 변수 기반 자동 채우기 지원
- 연결 테스트 기능 (SELECT 1 쿼리 실행)
- 설정 검증 및 세션 적용 기능

**주요 함수:**
- `render_db_section() -> None`
  - DB 연결 설정 섹션을 Streamlit UI로 렌더링

**의존성:**
- `interface.core.config`: DB 연결 레지스트리 조작
- `utils.databases.DatabaseFactory`: DB 커넥터 생성 및 연결 테스트
- `utils.databases.factory.load_config_from_env`: 환경 변수에서 설정 로드

**헬퍼 함수:**
- `_non_secret_fields(db_type: str) -> list[tuple[str, str]]`: DB 타입별 기본 필드 정의
- `_extra_non_secret_fields(db_type: str) -> list[tuple[str, str]]`: DB 타입별 추가 필드 정의
- `_secret_fields(db_type: str) -> list[tuple[str, str]]`: DB 타입별 비밀 필드 정의
- `_prefill_from_env(db_type: str, key: str) -> str`: 환경 변수에서 기본값 로드

### `llm_section.py`

LLM 및 Embedding 설정을 관리하는 UI 섹션을 제공합니다.

**주요 기능:**
- LLM 공급자 지원:
  - OpenAI, Azure OpenAI, AWS Bedrock, Gemini, Ollama, Hugging Face
- Embedding 공급자 지원 (동일한 공급자 목록)
- 공급자별 필드 동적 처리:
  - OpenAI: Model, API Key
  - Azure: Endpoint, Deployment(Model), API Version, API Key
  - Bedrock: Model, Access Key ID, Secret Access Key, Region
  - Gemini: Model, API Key (embedding만)
  - Ollama: Model, Base URL
  - Hugging Face: Endpoint URL, Repo ID, Model, API Token (또는 Embedding: Model, Repo ID, API Token)
- 프로파일 저장 기능:
  - LLM 프로파일 저장 (비밀키 제외 옵션)
  - Embedding 프로파일 저장 (시크릿 포함)
- 저장된 프로파일 목록 조회
- 환경 변수 및 세션 상태 기반 자동 채우기

**주요 함수:**
- `render_llm_section(config: Config | None = None) -> None`
  - LLM 및 Embedding 설정 섹션을 Streamlit UI로 렌더링
  - 2개 컬럼으로 나뉘어 Chat LLM과 Embeddings를 각각 설정
  - `config` 파라미터가 없으면 내부에서 `load_config()`를 호출하거나 None 처리

**의존성:**
- `interface.core.config`: LLM/Embedding 설정 및 프로파일 관리

**헬퍼 함수:**
- `_llm_fields(provider: str) -> list[tuple[str, str, bool]]`: LLM 공급자별 필드 정의 (label, env_key, is_secret)
- `_embedding_fields(provider: str) -> list[tuple[str, str, bool]]`: Embedding 공급자별 필드 정의

## 사용 방법

이 모듈들은 `interface.app_pages.settings.py`에서 import되어 사용됩니다.

### Import 예시

```python
from interface.app_pages.settings_sections.data_source_section import (
    render_data_source_section,
)
from interface.app_pages.settings_sections.llm_section import render_llm_section
from interface.app_pages.settings_sections.db_section import render_db_section
```

### 사용 예시

`settings.py`에서의 사용:

```python
from interface.core.config import load_config

config = load_config()

tabs = st.tabs(["데이터 소스", "LLM", "DB"])

with tabs[0]:
    render_data_source_section(config)

with tabs[1]:
    render_llm_section(config)

with tabs[2]:
    render_db_section()
```

### 함수 시그니처

#### `render_data_source_section(config: Config | None = None) -> None`
- **매개변수:**
  - `config` (Config | None): 설정 객체. None이면 내부에서 `load_config()` 호출
- **반환값:** None (Streamlit UI 직접 렌더링)

#### `render_db_section() -> None`
- **매개변수:** 없음
- **반환값:** None (Streamlit UI 직접 렌더링)

#### `render_llm_section(config: Config | None = None) -> None`
- **매개변수:**
  - `config` (Config | None): 설정 객체. None이면 내부에서 `load_config()` 호출하거나 None 처리
- **반환값:** None (Streamlit UI 직접 렌더링)

## 공통 특징

- 모든 섹션은 Streamlit을 사용하여 UI를 렌더링합니다.
- 설정 변경 시 `st.rerun()`을 호출하여 UI를 새로고침합니다.
- 에러 발생 시 `st.error()`를 사용하여 사용자에게 오류 메시지를 표시합니다.
- 성공적인 작업 완료 시 `st.success()`를 사용하여 확인 메시지를 표시합니다.
- 민감한 정보(비밀번호, API 키 등)는 `type="password"`를 사용하여 마스킹 처리합니다.

