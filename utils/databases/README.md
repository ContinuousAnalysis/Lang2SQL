# Databases 모듈

다양한 데이터베이스에 대한 연결 및 SQL 실행 기능을 제공하는 유틸리티 모듈입니다.

## 디렉토리 구조

```
databases/
├── __init__.py
├── config.py
├── factory.py
├── logger.py
└── connector/
    ├── base_connector.py
    ├── clickhouse_connector.py
    ├── databricks_connector.py
    ├── duckdb_connector.py
    ├── mariadb_connector.py
    ├── mysql_connector.py
    ├── oracle_connector.py
    ├── postgres_connector.py
    ├── snowflake_connector.py
    ├── sqlite_connector.py
    ├── trino_connector.py
    └── README.md
```

## 파일 설명

### __init__.py

데이터베이스 유틸리티 패키지 초기화 모듈입니다. 주요 구성 요소를 외부로 노출합니다.

**Export:**
- `DatabaseFactory`: 데이터베이스 커넥터 팩토리 클래스
- `DBConfig`: 데이터베이스 설정 타입

**사용처:**
- `interface/app_pages/settings_sections/db_section.py`: DB 설정 인터페이스에서 import
- 다른 모듈에서 `from utils.databases import DatabaseFactory` 형태로 import되어 사용됨

### config.py

데이터베이스 연결 설정 정보를 정의하는 모듈입니다.

**클래스:**
- `DBConfig(TypedDict)`: 데이터베이스 연결 설정 정보를 표현하는 타입 딕셔너리
  - `host` (str): 데이터베이스 호스트명 또는 IP 주소
  - `port` (Optional[int]): 데이터베이스 포트 번호
  - `user` (Optional[str]): 접속 사용자명
  - `password` (Optional[str]): 접속 비밀번호
  - `database` (Optional[str]): 대상 데이터베이스 이름
  - `extra` (Optional[Dict[str, str]]): 드라이버별 추가 설정값

**사용처:**
- `utils.databases.factory`: DBConfig 타입을 사용하여 설정 정보 전달
- `utils.databases.connector.*`: 모든 커넥터가 이 타입을 사용
- `interface/core/config/models.py`: DBConnectionProfile 모델에서 참조

### factory.py

데이터베이스 커넥터 팩토리 모듈입니다. DB 타입에 따라 알맞은 커넥터 클래스를 동적으로 로드하고 인스턴스를 생성합니다.

**클래스:**
- `DatabaseFactory`: 데이터베이스 커넥터 팩토리 클래스
  - `get_connector(db_type, config)`: 주어진 DB 타입에 해당하는 Connector 인스턴스 반환
    - DB 타입이 지정되지 않은 경우 환경 변수(`DB_TYPE`)에서 자동으로 가져옴
    - config가 지정되지 않은 경우 `load_config_from_env()`로 환경 변수에서 로드
    - 지원되지 않는 DB 타입이거나 모듈을 로드할 수 없는 경우 `ValueError` 발생

**함수:**
- `load_config_from_env(prefix) -> DBConfig`: 환경변수에서 데이터베이스 접속 설정을 로드
  - prefix: 환경변수 접두어 (예: 'POSTGRES', 'MYSQL')
  - `{PREFIX}_HOST`, `{PREFIX}_PORT`, `{PREFIX}_USER`, `{PREFIX}_PASSWORD`, `{PREFIX}_DATABASE` 로드
  - 추가 커스텀 환경변수는 `extra` 필드에 포함

**사용처:**
- `interface/app_pages/settings_sections/db_section.py`: DB 연결 테스트 및 설정 적용 (221번 라인)
- `interface/app_pages/settings_sections/db_section.py`: 환경변수 설정 검증 (272번 라인)
- `utils.databases.__init__.py`: DatabaseFactory를 외부로 노출

**환경변수 예시:**
```bash
DB_TYPE=postgres
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=myuser
POSTGRES_PASSWORD=mypassword
POSTGRES_DATABASE=mydb
```

### logger.py

로깅 설정 모듈입니다. 애플리케이션 전역에서 사용할 기본 로깅 설정을 정의합니다.

**내보내기:**
- `logger`: 표준 로거 인스턴스

**설정:**
- 레벨: `INFO`
- 포맷: `%(asctime)s [%(levelname)s] %(message)s`
- 날짜 포맷: `%Y-%m-%d %H:%M:%S`

**사용처:**
- `utils.databases.factory`: DB 타입 로딩 실패 시 로깅
- `utils.databases.connector.*`: 모든 커넥터에서 연결 및 SQL 실행 로깅

### connector/

데이터베이스별 커넥터 구현이 위치한 디렉토리입니다.

자세한 내용은 [connector/README.md](connector/README.md)를 참조하세요.

**주요 특징:**
- 모든 커넥터는 `BaseConnector` 추상 클래스를 상속
- 공통 인터페이스: `connect()`, `run_sql(sql) -> pd.DataFrame`, `close()`
- 지원 데이터베이스: PostgreSQL, MySQL, MariaDB, Oracle, SQLite, DuckDB, Snowflake, Databricks, Trino, ClickHouse

## 사용 방법

### Factory 패턴 사용 (권장)

환경 변수를 설정하고 DatabaseFactory를 사용하여 커넥터를 생성합니다:

```python
from utils.databases import DatabaseFactory

# 환경 변수 사용
connector = DatabaseFactory.get_connector()
result = connector.run_sql("SELECT * FROM users LIMIT 10")
connector.close()
```

### 명시적 설정 사용

DBConfig를 직접 생성하여 전달할 수 있습니다:

```python
from utils.databases import DatabaseFactory, DBConfig

config = DBConfig(
    host="localhost",
    port=5432,
    user="myuser",
    password="mypassword",
    database="mydb",
    extra={}
)
connector = DatabaseFactory.get_connector(db_type="postgres", config=config)
result = connector.run_sql("SELECT * FROM users LIMIT 10")
connector.close()
```

### 직접 커넥터 사용

특정 커넥터를 직접 import하여 사용할 수 있습니다:

```python
from utils.databases.connector.postgres_connector import PostgresConnector
from utils.databases.config import DBConfig

config = DBConfig(
    host="localhost",
    port=5432,
    user="myuser",
    password="mypassword",
    database="mydb",
    extra={}
)

connector = PostgresConnector(config)
result = connector.run_sql("SELECT * FROM users LIMIT 10")
print(result)
connector.close()
```

## 지원되는 데이터베이스

1. **PostgreSQL** (`postgres`)
2. **MySQL** (`mysql`)
3. **MariaDB** (`mariadb`)
4. **Oracle** (`oracle`)
5. **SQLite** (`sqlite`)
6. **DuckDB** (`duckdb`)
7. **Snowflake** (`snowflake`)
8. **Databricks** (`databricks`)
9. **Trino** (`trino`)
10. **ClickHouse** (`clickhouse`)

각 데이터베이스의 상세한 설정 방법은 [connector/README.md](connector/README.md)를 참조하세요.

## 통합 사용 예시

### Streamlit 인터페이스에서 사용

`interface/app_pages/settings_sections/db_section.py`에서 DB 연결을 설정하고 테스트:

```python
from utils.databases import DatabaseFactory

# 연결 테스트
connector = DatabaseFactory.get_connector(db_type=db_type)
test_sql = "SELECT 1"
df = connector.run_sql(test_sql)
connector.close()
```

### CLI에서 사용

환경 변수를 통해 커넥터를 생성하고 SQL 쿼리를 실행할 수 있습니다.

## 에러 처리

- **연결 실패**: `ConnectionError` 발생
- **SQL 실행 실패**: `RuntimeError` 발생
- **지원되지 않는 DB 타입**: `ValueError` 발생
- **DB_TYPE 미지정**: `ValueError("DB_TYPE이 환경변수 또는 인자로 제공되어야 합니다.")` 발생

## 로깅

모든 커넥터는 `utils.databases.logger`를 사용하여 다음 정보를 로깅합니다:
- 연결 성공/실패
- SQL 실행 결과
- 에러 발생 상황

로그 포맷: `YYYY-MM-DD HH:MM:SS [LEVEL] 메시지`

## 의존성

각 커넥터는 해당 데이터베이스의 Python 드라이버를 필요로 합니다:

- PostgreSQL: `psycopg2`
- MySQL/MariaDB: `mysql-connector-python`
- Oracle: `oracledb`
- SQLite: `sqlite3` (표준 라이브러리)
- DuckDB: `duckdb`
- Snowflake: `snowflake-connector-python`
- Databricks: `databricks-sql-connector`
- Trino: `trino`
- ClickHouse: `clickhouse-driver`

## 확장성

새로운 데이터베이스를 추가하려면:

1. `connector/` 디렉토리에 `{db_type}_connector.py` 파일 생성
2. `BaseConnector`를 상속받는 `{DBType}Connector` 클래스 구현
3. `connect()`, `run_sql(sql) -> pd.DataFrame`, `close()` 메서드 구현
4. `DatabaseFactory.get_connector()`가 자동으로 새 커넥터를 로드

자세한 내용은 `connector/base_connector.py`를 참조하세요.
