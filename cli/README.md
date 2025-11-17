# CLI 모듈

Lang2SQL 프로젝트의 CLI(Command Line Interface) 모듈입니다. 자연어 질문을 SQL 쿼리로 변환하고, Streamlit 웹 애플리케이션을 실행하는 기능을 제공합니다.

## 디렉토리 구조

```
cli/
├── __init__.py           # CLI 진입점 및 메인 그룹 정의
├── __pycache__/          # Python 캐시 디렉토리
├── commands/             # CLI 명령어 정의 모듈
│   ├── __pycache__/
│   ├── quary.py          # 자연어 질문을 SQL로 변환하는 명령어
│   ├── run_streamlit.py  # Streamlit 실행 명령어
│   └── README.md         # Commands 모듈 문서
├── core/                 # CLI 핵심 기능 모듈
│   ├── __pycache__/
│   ├── environment.py    # 환경 변수 초기화 모듈
│   ├── streamlit_runner.py # Streamlit 실행 유틸리티
│   └── README.md         # Core 모듈 문서
├── utils/                # CLI 유틸리티 모듈
│   ├── __pycache__/
│   ├── env_loader.py     # 환경 변수 로드 유틸리티
│   ├── logger.py         # 로깅 설정 유틸리티
│   └── README.md         # Utils 모듈 문서
└── README.md             # 이 파일
```

## 모듈 개요

### `__init__.py`

CLI 프로그램의 진입점입니다. Click 프레임워크를 사용하여 명령어 그룹과 옵션을 정의합니다.

**주요 구성 요소:**

#### CLI 그룹 정의
- **함수**: `cli(ctx, datahub_server, run_streamlit, port, env_file_path, prompt_dir_path, vectordb_type, vectordb_location)`
- **데코레이터**: `@click.group()`
- **역할**: Lang2SQL CLI의 최상위 명령어 그룹

#### 주요 옵션

1. **`--version` / `-v`**: 버전 정보 출력
2. **`--datahub_server`** (Deprecated): DataHub GMS URL 설정 - 더 이상 사용되지 않음
3. **`--run-streamlit`**: CLI 실행 시 Streamlit 애플리케이션을 바로 실행하는 플래그
4. **`-p, --port`**: Streamlit 서버 포트 번호 (기본값: 8501)
5. **`--env-file-path`**: 환경 변수를 로드할 .env 파일 경로
6. **`--prompt-dir-path`**: 프롬프트 템플릿 디렉토리 경로
7. **`--vectordb-type`** (Deprecated): VectorDB 타입 - 더 이상 사용되지 않음
8. **`--vectordb-location`** (Deprecated): VectorDB 위치 - 더 이상 사용되지 않음

#### 주요 동작

1. **환경 변수 초기화**: `initialize_environment()` 호출로 환경 변수 설정
2. **Deprecated 옵션 경고**: 사용되지 않는 옵션 사용 시 경고 메시지 출력
3. **Streamlit 자동 실행**: `--run-streamlit` 플래그가 설정된 경우 Streamlit 실행

#### 등록된 명령어

- `run-streamlit`: Streamlit 애플리케이션 실행 (`cli/commands/run_streamlit.py`)
- `query`: 자연어 질문을 SQL 쿼리로 변환 (`cli/commands/quary.py`)

#### Import 관계

**Import하는 모듈:**
- `cli.commands.quary.query_command`: query 명령어
- `cli.commands.run_streamlit.run_streamlit_cli_command`: run-streamlit 명령어
- `cli.core.environment.initialize_environment`: 환경 변수 초기화
- `cli.core.streamlit_runner.run_streamlit_command`: Streamlit 실행 함수
- `cli.utils.logger.configure_logging`: 로깅 설정
- `version.__version__`: 버전 정보

**사용 위치:**
- CLI 진입점: `pyproject.toml`의 `[project.scripts]` 섹션에 정의됨
  ```toml
  [project.scripts]
  lang2sql = "cli.__init__:cli"
  ```
- 사용 방법: 패키지 설치 후 `lang2sql` 명령어로 실행
  ```bash
  lang2sql --help
  lang2sql --version
  lang2sql --run-streamlit
  lang2sql query "질문"
  lang2sql run-streamlit
  ```

#### 코드 예시

```python
from cli import cli

# CLI 그룹 자동 등록
# lang2sql 명령어로 실행 가능
```

### 하위 모듈

#### `commands/` 모듈

CLI 명령어를 정의하는 모듈입니다. 자연어 질문을 SQL로 변환하는 `query` 명령어와 Streamlit을 실행하는 `run-streamlit` 명령어를 제공합니다.

자세한 내용은 [`commands/README.md`](commands/README.md)를 참고하세요.

**주요 파일:**
- `quary.py`: `query_command` - 자연어를 SQL로 변환하는 명령어
- `run_streamlit.py`: `run_streamlit_cli_command` - Streamlit 실행 명령어

**사용 위치:**
- `cli/__init__.py` (10-11, 116-117번 라인): CLI 그룹에 명령어 등록
  ```python
  from cli.commands.quary import query_command
  from cli.commands.run_streamlit import run_streamlit_cli_command
  
  cli.add_command(run_streamlit_cli_command)
  cli.add_command(query_command)
  ```

#### `core/` 모듈

CLI의 핵심 기능을 제공하는 모듈입니다. 환경 변수 초기화와 Streamlit 실행 기능을 담당합니다.

자세한 내용은 [`core/README.md`](core/README.md)를 참고하세요.

**주요 파일:**
- `environment.py`: `initialize_environment` - 환경 변수 초기화 함수
- `streamlit_runner.py`: `run_streamlit_command` - Streamlit 실행 함수

**사용 위치:**
- `cli/__init__.py` (12-13, 85, 113번 라인):
  ```python
  from cli.core.environment import initialize_environment
  from cli.core.streamlit_runner import run_streamlit_command
  
  # 환경 변수 초기화
  initialize_environment(
      env_file_path=env_file_path, 
      prompt_dir_path=prompt_dir_path
  )
  
  # Streamlit 실행
  if run_streamlit:
      run_streamlit_command(port)
  ```

#### `utils/` 모듈

CLI 애플리케이션에서 사용되는 유틸리티 함수들을 제공하는 모듈입니다.

자세한 내용은 [`utils/README.md`](utils/README.md)를 참고하세요.

**주요 파일:**
- `env_loader.py`: 환경 변수 로드 및 설정 함수들
  - `load_env`: .env 파일 로드
  - `set_prompt_dir`: 프롬프트 디렉토리 설정
  - `set_vectordb`: VectorDB 설정
- `logger.py`: `configure_logging` - CLI 전용 로깅 설정

**사용 위치:**
- `cli/__init__.py` (14, 18번 라인): 로깅 설정
  ```python
  from cli.utils.logger import configure_logging
  
  logger = configure_logging()
  ```
- `cli/core/environment.py`: 환경 변수 로드
- `cli/core/streamlit_runner.py`: 로깅 설정
- `cli/commands/quary.py`: 로깅 설정
- `cli/commands/run_streamlit.py`: 로깅 설정

## CLI 사용 방법

### 기본 사용법

```bash
# 도움말 보기
lang2sql --help

# 버전 확인
lang2sql --version

# Streamlit 바로 실행
lang2sql --run-streamlit

# 환경 변수 파일 지정하여 실행
lang2sql --env-file-path /path/to/.env --run-streamlit
```

### 명령어

#### `query` 명령어

자연어 질문을 SQL 쿼리로 변환합니다.

```bash
# 기본 사용
lang2sql query "고객 데이터를 기반으로 유니크한 유저 수를 카운트하는 쿼리"

# 옵션과 함께 사용
lang2sql query "질문" \
  --database-env clickhouse \
  --retriever-name 기본 \
  --top-n 5 \
  --device cpu \
  --use-enriched-graph \
  --vectordb-type faiss \
  --vectordb-location ./dev/table_info_db
```

#### `run-streamlit` 명령어

Streamlit 웹 애플리케이션을 실행합니다.

```bash
# 기본 포트(8501)로 실행
lang2sql run-streamlit

# 특정 포트로 실행
lang2sql run-streamlit -p 9000
```

자세한 사용법은 [`commands/README.md`](commands/README.md)를 참고하세요.

## 의존성

### 내부 의존성

- `cli.commands.*`: CLI 명령어 정의
- `cli.core.*`: 핵심 기능 모듈
- `cli.utils.*`: 유틸리티 함수
- `version`: 버전 정보

### 외부 의존성

- `click`: CLI 프레임워크
- `subprocess`: Streamlit 프로세스 실행 (core 모듈)
- `python-dotenv`: 환경 변수 파일 로드 (utils 모듈)
- `streamlit`: Streamlit 웹 애플리케이션 프레임워크

## 모듈 간 관계도

```
cli/__init__.py (진입점)
├── commands/
│   ├── quary.py → engine.query_executor
│   └── run_streamlit.py → core/streamlit_runner.py
├── core/
│   ├── environment.py → utils/env_loader.py
│   └── streamlit_runner.py → utils/logger.py
└── utils/
    ├── env_loader.py (독립적)
    └── logger.py (독립적)
```

## 주요 특징

1. **모듈화된 구조**: 명령어, 핵심 기능, 유틸리티가 명확히 분리됨
2. **확장 가능성**: 새로운 명령어를 쉽게 추가할 수 있는 구조
3. **환경 관리**: 일관된 환경 변수 초기화 보장
4. **UI 중심 설계**: VectorDB 및 DataHub 설정은 UI에서 관리
5. **로깅 지원**: 모든 모듈에서 일관된 로깅 사용
6. **Deprecated 옵션 처리**: 사용되지 않는 옵션에 대한 명확한 경고

## 참고 문서

- [`commands/README.md`](commands/README.md): 명령어 모듈 상세 문서
- [`core/README.md`](core/README.md): 핵심 기능 모듈 상세 문서
- [`utils/README.md`](utils/README.md): 유틸리티 모듈 상세 문서

