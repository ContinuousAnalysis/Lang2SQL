# CLI Utils 모듈

CLI 애플리케이션에서 사용되는 유틸리티 함수들을 제공하는 모듈입니다.

## 디렉토리 구조

```
cli/utils/
├── __pycache__/
├── env_loader.py
├── logger.py
└── README.md
```

## 파일 목록 및 설명

### env_loader.py

환경 변수 유틸리티 모듈입니다. `.env` 파일 로드, 프롬프트 디렉토리 설정, VectorDB 타입 및 위치 설정을 제공합니다.

**주요 함수:**

#### `load_env(env_file_path: Optional[str] = None) -> None`
환경 변수 파일(.env)을 로드합니다.

**파라미터:**
- `env_file_path` (Optional[str]): .env 파일 경로. None이면 기본 경로 사용.

**동작:**
- 지정된 경로의 `.env` 파일을 로드하거나, 경로가 없으면 기본 경로의 `.env` 파일을 로드합니다.
- 성공/실패 메시지를 컬러로 출력합니다.
- 로드 실패 시 예외를 발생시킵니다.

**사용 예시:**
```python
from cli.utils.env_loader import load_env

# 기본 .env 파일 로드
load_env()

# 특정 경로의 .env 파일 로드
load_env(env_file_path="/path/to/.env")
```

#### `set_prompt_dir(prompt_dir_path: Optional[str]) -> None`
프롬프트 템플릿 디렉토리 경로를 환경 변수로 설정합니다.

**파라미터:**
- `prompt_dir_path` (Optional[str]): 디렉토리 경로. None이면 설정하지 않음.

**환경 변수:**
- `PROMPT_TEMPLATES_DIR`: 설정된 프롬프트 디렉토리 경로

**Raises:**
- `ValueError`: 경로가 유효하지 않을 경우

**사용 예시:**
```python
from cli.utils.env_loader import set_prompt_dir

set_prompt_dir(prompt_dir_path="/path/to/prompt/templates")
```

#### `set_vectordb(vectordb_type: str, vectordb_location: Optional[str] = None) -> None`
VectorDB 타입과 위치를 환경 변수로 설정합니다.

**파라미터:**
- `vectordb_type` (str): VectorDB 타입 ("faiss" 또는 "pgvector")
- `vectordb_location` (Optional[str]): 경로 또는 연결 URL

**환경 변수:**
- `VECTORDB_TYPE`: 설정된 VectorDB 타입
- `VECTORDB_LOCATION`: 설정된 VectorDB 경로 또는 연결 URL (지정된 경우)

**Raises:**
- `ValueError`: 잘못된 타입이나 경로/URL일 경우

**사용 예시:**
```python
from cli.utils.env_loader import set_vectordb

# FAISS 설정
set_vectordb(vectordb_type="faiss", vectordb_location="/path/to/faiss/db")

# pgvector 설정
set_vectordb(
    vectordb_type="pgvector",
    vectordb_location="postgresql://user:pass@host:port/db"
)
```

**사용처:**
- `cli/core/environment.py` (5번 라인): `load_env`, `set_prompt_dir` 함수를 import하여 사용
  - `initialize_environment` 함수에서 환경 변수 초기화 시 사용
  ```python
  from cli.utils.env_loader import load_env, set_prompt_dir
  
  def initialize_environment(
      *,
      env_file_path: Optional[str],
      prompt_dir_path: Optional[str],
  ) -> None:
      load_env(env_file_path=env_file_path)
      set_prompt_dir(prompt_dir_path=prompt_dir_path)
  ```

### logger.py

CLI 전용 로깅 유틸리티 모듈입니다. 로깅 설정을 구성하고 기본 로거 인스턴스를 반환합니다.

**주요 함수:**

#### `configure_logging(level: int = logging.INFO) -> logging.Logger`
로깅을 설정하고 기본 로거를 반환합니다.

**파라미터:**
- `level` (int, optional): 로깅 레벨. 기본값은 `logging.INFO`.

**반환값:**
- `logging.Logger`: 설정된 로거 인스턴스. 로거 이름은 "cli"입니다.

**로깅 설정:**
- 레벨: 지정된 레벨 (기본값: `INFO`)
- 포맷: `%(asctime)s [%(levelname)s] %(message)s`
- 날짜 포맷: `%Y-%m-%d %H:%M:%S`

**사용 예시:**
```python
from cli.utils.logger import configure_logging

# 기본 설정으로 로거 생성
logger = configure_logging()

# DEBUG 레벨로 로거 생성
logger = configure_logging(level=logging.DEBUG)

# 로깅 사용
logger.info("Information message")
logger.error("Error message")
```

**사용처:**

1. **`cli/__init__.py`** (14번 라인)
   - CLI 진입점에서 로거 초기화
   ```python
   from cli.utils.logger import configure_logging
   
   logger = configure_logging()
   ```
   - 사용 위치: 18번 라인에서 로거 인스턴스 생성, 89번, 92번 라인에서 에러 및 정보 로깅

2. **`cli/commands/quary.py`** (11번 라인)
   - query 명령어 실행 시 로거 초기화
   ```python
   from cli.utils.logger import configure_logging
   
   logger = configure_logging()
   ```
   - 사용 위치: 13번 라인에서 로거 인스턴스 생성, 112번 라인에서 에러 로깅

3. **`cli/core/streamlit_runner.py`** (5번 라인)
   - Streamlit 실행 모듈에서 로거 초기화
   ```python
   from cli.utils.logger import configure_logging
   
   logger = configure_logging()
   ```
   - 사용 위치: 7번 라인에서 로거 인스턴스 생성, 19번, 33번, 35번 라인에서 정보 및 에러 로깅

4. **`cli/commands/run_streamlit.py`** (6번 라인)
   - run-streamlit 명령어 실행 시 로거 초기화
   ```python
   from cli.utils.logger import configure_logging
   
   logger = configure_logging()
   ```
   - 사용 위치: 8번 라인에서 로거 인스턴스 생성, 28번 라인에서 정보 로깅

## 의존성

- `click`: CLI 출력 및 메시지 표시
- `dotenv`: `.env` 파일 로드
- `logging`: 로깅 기능 (Python 표준 라이브러리)
- `pathlib.Path`: 경로 처리
- `os`: 환경 변수 설정

