# CLI Commands 모듈

Lang2SQL CLI 애플리케이션에서 사용되는 명령어 정의 모듈입니다.

이 모듈은 사용자가 CLI를 통해 Lang2SQL 기능을 사용할 수 있도록 다양한 명령어를 제공합니다.

## 디렉토리 구조

```
cli/commands/
├── __pycache__/                  # Python 캐시 디렉토리
├── quary.py                      # 자연어 질문을 SQL로 변환하는 명령어
├── run_streamlit.py              # Streamlit 실행 명령어
└── README.md                     # 이 파일
```

## 모듈 개요

### `quary.py`
- **위치**: `cli/commands/quary.py`
- **설명**: 자연어 질문을 SQL 쿼리로 변환하는 CLI 명령어 정의 모듈
- **주요 기능**: 
  - 사용자가 입력한 자연어 질문을 SQL 쿼리로 변환
  - 다양한 옵션을 통한 쿼리 실행 파라미터 설정
  - SQL 쿼리 결과 출력

#### 주요 함수

##### `query_command()`
자연어 질문을 SQL 쿼리로 변환하여 출력합니다.

**매개변수:**
- `question` (str): SQL로 변환할 자연어 질문
- `database_env` (str, optional): 사용할 데이터베이스 환경 (기본값: "clickhouse")
- `retriever_name` (str, optional): 테이블 검색기 이름 (기본값: "기본")
- `top_n` (int, optional): 검색된 상위 테이블 수 제한 (기본값: 5)
- `device` (str, optional): LLM 실행에 사용할 디바이스 (기본값: "cpu")
- `use_enriched_graph` (bool, optional): 확장된 그래프(프로파일 추출 + 컨텍스트 보강) 사용 여부
- `vectordb_type` (str, optional): 사용할 벡터 데이터베이스 타입 ("faiss" 또는 "pgvector", 기본값: "faiss")
- `vectordb_location` (str, optional): VectorDB 위치 설정
  - FAISS: 디렉토리 경로 (예: ./my_vectordb)
  - pgvector: 연결 문자열 (예: postgresql://user:pass@host:port/db)
  - 기본값: FAISS는 './dev/table_info_db', pgvector는 환경변수 사용

**동작 방식:**
1. 환경 변수 설정 (VECTORDB_TYPE, VECTORDB_LOCATION)
2. `engine.query_executor.execute_query()` 호출하여 쿼리 실행
3. `extract_sql_from_result()`로 SQL 추출
4. 추출 실패 시 전체 generated_query 출력
5. 성공 시 SQL 쿼리 출력

**사용 예제:**
```bash
# 기본 사용
lang2sql query "고객 데이터를 기반으로 유니크한 유저 수를 카운트하는 쿼리"

# 옵션 사용
lang2sql query "고객 데이터를 기반으로 유니크한 유저 수를 카운트하는 쿼리" \
  --database-env clickhouse \
  --retriever-name 기본 \
  --top-n 5 \
  --device cpu \
  --use-enriched-graph

# VectorDB 지정
lang2sql query "고객 데이터를 기반으로 유니크한 유저 수를 카운트하는 쿼리" \
  --vectordb-type pgvector \
  --vectordb-location postgresql://user:pass@localhost:5432/db
```

### `run_streamlit.py`
- **위치**: `cli/commands/run_streamlit.py`
- **설명**: Streamlit 실행 CLI 명령어 모듈
- **주요 기능**:
  - CLI 명령어로 Streamlit 애플리케이션 실행
  - 포트 번호 지정 가능

#### 주요 함수

##### `run_streamlit_cli_command()`
CLI 명령어로 Streamlit 애플리케이션을 실행합니다.

**매개변수:**
- `port` (int, optional): Streamlit 서버가 바인딩될 포트 번호 (기본값: 8501)

**동작 방식:**
1. 로깅을 통해 실행 시작 로그 기록
2. `cli.core.streamlit_runner.run_streamlit_command()` 호출하여 Streamlit 실행

**사용 예제:**
```bash
# 기본 포트(8501)로 실행
lang2sql run-streamlit

# 사용자 지정 포트로 실행
lang2sql run-streamlit -p 9000

# 또는
lang2sql run-streamlit --port 9000
```

## 의존성

### 내부 모듈
- `cli.utils.logger.configure_logging`: CLI 전용 로깅 유틸리티
- `cli.core.streamlit_runner.run_streamlit_command`: Streamlit 실행 유틸리티
- `engine.query_executor.execute_query`: 쿼리 실행 공용 함수
- `engine.query_executor.extract_sql_from_result`: SQL 추출 함수

### 외부 라이브러리
- `click`: CLI 프레임워크
- `os`: 환경 변수 설정을 위한 표준 라이브러리

## 사용 위치

### 1. CLI 메인 모듈 (`cli/__init__.py`)
CLI 메인 모듈에서 두 명령어를 등록합니다.

```python
from cli.commands.quary import query_command
from cli.commands.run_streamlit import run_streamlit_cli_command

# CLI 그룹에 명령어 추가
cli.add_command(run_streamlit_cli_command)
cli.add_command(query_command)
```

## CLI 사용 방법

### `query` 명령어

자연어 질문을 SQL 쿼리로 변환하는 명령어입니다.

**기본 사용법:**
```bash
lang2sql query "<자연어 질문>"
```

**모든 옵션:**
```bash
lang2sql query "<자연어 질문>" \
  --database-env <데이터베이스 환경> \
  --retriever-name <검색기 이름> \
  --top-n <테이블 수> \
  --device <cpu|cuda> \
  --use-enriched-graph \
  --vectordb-type <faiss|pgvector> \
  --vectordb-location <경로 또는 연결 문자열>
```

**실제 사용 예:**
```bash
# 간단한 쿼리
lang2sql query "사용자 수를 확인하는 쿼리"

# 옵션을 사용한 쿼리
lang2sql query "고객 데이터를 기반으로 유니크한 유저 수를 카운트하는 쿼리" \
  --database-env clickhouse \
  --top-n 10 \
  --use-enriched-graph
```

### `run-streamlit` 명령어

Streamlit 웹 인터페이스를 실행하는 명령어입니다.

**기본 사용법:**
```bash
lang2sql run-streamlit
```

**포트 지정:**
```bash
lang2sql run-streamlit -p 9000
```

**실제 사용 예:**
```bash
# 기본 포트로 실행
lang2sql run-streamlit

# 다른 포트로 실행
lang2sql run-streamlit --port 9000

# 브라우저에서 http://localhost:9000 접속
```

## 워크플로우

### `query` 명령어 워크플로우
1. 사용자가 자연어 질문과 옵션을 CLI로 입력
2. VectorDB 타입과 위치 환경 변수 설정
3. `engine.query_executor.execute_query()` 호출
4. Lang2SQL 파이프라인 실행
5. SQL 추출 및 출력

### `run-streamlit` 명령어 워크플로우
1. 사용자가 명령어 실행
2. `cli.core.streamlit_runner.run_streamlit_command()` 호출
3. Streamlit 서브프로세스 실행
4. 웹 브라우저에서 접속 가능

## 환경 변수

### `query` 명령어에서 설정되는 환경 변수
- `VECTORDB_TYPE`: 벡터 데이터베이스 타입 ("faiss" 또는 "pgvector")
- `VECTORDB_LOCATION`: 벡터 데이터베이스 위치 (FAISS: 디렉토리 경로, pgvector: 연결 문자열)

## 로깅

모든 명령어는 `cli.utils.logger.configure_logging()`을 사용하여 로그를 기록합니다:

- `query` 명령어: 쿼리 처리 중 오류 발생 시 에러 로그
- `run-streamlit` 명령어: 실행 시작 로그

## 에러 처리

### `query` 명령어
- `Exception` 발생 시 에러 로그 기록 및 예외 재발생
- SQL 추출 실패 시 전체 generated_query 출력 시도

### `run-streamlit` 명령어
- `subprocess.CalledProcessError` 발생 시 에러 로그 기록 및 예외 재발생

## 주의사항

1. `query` 명령어는 SQL 쿼리만 출력하며 결과는 실행하지 않습니다
2. `vectordb_location`을 지정하지 않으면 기본값 또는 환경변수 사용
3. `run-streamlit` 명령어는 서브프로세스로 Streamlit을 실행하므로 프로세스가 종료될 때까지 대기합니다
4. 기본 포트(8501)가 이미 사용 중이면 포트 변경 필요
5. `use_enriched_graph` 옵션 사용 시 더 많은 리소스 소모 가능

