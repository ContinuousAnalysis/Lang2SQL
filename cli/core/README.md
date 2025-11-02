# CLI Core 모듈

Lang2SQL CLI의 핵심 기능을 제공하는 모듈입니다.

## 디렉토리 구조

```
cli/core/
├── environment.py      # 환경 변수 초기화 모듈
└── streamlit_runner.py # Streamlit 실행 유틸리티 모듈
```

## 모듈 설명

### 1. environment.py

환경 변수 초기화를 담당하는 모듈입니다. VectorDB 설정은 UI에서 관리합니다.

#### 주요 기능

- `initialize_environment()`: 환경 변수를 초기화하는 함수

#### 함수 상세

##### `initialize_environment(env_file_path, prompt_dir_path)`

환경 변수를 초기화합니다. VectorDB 설정은 UI에서 관리합니다.

**매개변수:**
- `env_file_path` (Optional[str]): 로드할 .env 파일 경로. None이면 기본값 사용.
- `prompt_dir_path` (Optional[str]): 프롬프트 템플릿 디렉토리 경로. None이면 설정하지 않음.

**예외:**
- `Exception`: 초기화 과정에서 오류가 발생한 경우.

**내부 동작:**
- `cli.utils.env_loader.load_env()`: .env 파일을 로드합니다.
- `cli.utils.env_loader.set_prompt_dir()`: 프롬프트 템플릿 디렉토리 경로를 환경 변수로 설정합니다.

#### 사용 예시

```python
from cli.core.environment import initialize_environment

# 기본 경로로 초기화
initialize_environment(env_file_path=None, prompt_dir_path=None)

# 사용자 정의 경로로 초기화
initialize_environment(
    env_file_path="/path/to/.env",
    prompt_dir_path="/path/to/prompts"
)
```

#### import 및 사용 위치

이 모듈의 `initialize_environment` 함수는 다음과 같이 사용됩니다:

- **`cli/__init__.py`** (85-90번째 줄): CLI 진입점에서 환경 초기화 시 호출
  ```python
  from cli.core.environment import initialize_environment
  
  initialize_environment(
      env_file_path=env_file_path, 
      prompt_dir_path=prompt_dir_path
  )
  ```

### 2. streamlit_runner.py

Streamlit 애플리케이션 실행을 담당하는 유틸리티 모듈입니다.

#### 주요 기능

- `run_streamlit_command()`: 지정된 포트에서 Streamlit 애플리케이션을 실행하는 함수

#### 함수 상세

##### `run_streamlit_command(port)`

지정된 포트에서 Streamlit 애플리케이션을 실행합니다.

**매개변수:**
- `port` (int): 바인딩할 포트 번호.

**예외:**
- `subprocess.CalledProcessError`: 실행 실패 시 발생.

**내부 동작:**
- `subprocess.run()`을 사용하여 `streamlit run` 명령을 실행합니다.
- 실행 대상: `interface/streamlit_app.py`
- 서버 주소: `0.0.0.0`
- 포트: 사용자 지정 값 (기본값: 8501)
- 로깅: `cli.utils.logger.configure_logging()`을 통해 로그 출력

#### 사용 예시

```python
from cli.core.streamlit_runner import run_streamlit_command

# 기본 포트(8501)로 실행
run_streamlit_command(port=8501)

# 사용자 정의 포트로 실행
run_streamlit_command(port=8080)
```

#### import 및 사용 위치

이 모듈의 `run_streamlit_command` 함수는 다음과 같이 사용됩니다:

1. **`cli/__init__.py`** (113번째 줄): CLI의 `--run-streamlit` 옵션이 활성화된 경우 호출
   ```python
   from cli.core.streamlit_runner import run_streamlit_command
   
   if run_streamlit:
       run_streamlit_command(port)
   ```

2. **`cli/commands/run_streamlit.py`** (29번째 줄): `run-streamlit` CLI 명령 실행 시 호출
   ```python
   from cli.core.streamlit_runner import run_streamlit_command
   
   @click.command(name="run-streamlit")
   def run_streamlit_cli_command(port: int):
       logger.info("Executing 'run-streamlit' command on port %d...", port)
       run_streamlit_command(port)
   ```

## 의존성

### 내부 의존성

- `cli.utils.env_loader`: 환경 변수 로드 및 프롬프트 디렉토리 설정
- `cli.utils.logger`: 로깅 설정

### 외부 의존성

- `subprocess`: 프로세스 실행 (streamlit_runner.py)

## 주요 특징

1. **환경 관리**: CLI 진입점에서 일관된 환경 변수 초기화 보장
2. **UI 중심 설계**: VectorDB 설정은 UI에서 관리하여 사용자 편의성 향상
3. **유연한 실행**: 다양한 포트에서 Streamlit 애플리케이션 실행 지원
4. **로깅 지원**: 실행 상태 및 오류 추적 가능

