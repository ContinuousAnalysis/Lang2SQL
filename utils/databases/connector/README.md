# Connector 모듈

데이터베이스 연결 및 SQL 실행을 위한 커넥터 클래스들을 제공하는 모듈입니다.

## 디렉토리 구조

```
connector/
├── __pycache__/
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
└── trino_connector.py
```

## 파일 설명

### base_connector.py

데이터베이스 커넥터의 기본 인터페이스를 정의하는 모듈입니다.

**클래스:**
- `BaseConnector`: 모든 DB 커넥터가 상속받아야 하는 추상 클래스
  - `connection`: DB 연결 객체를 저장하는 클래스 변수
  - `connect()`: 데이터베이스 연결 수행 (abstractmethod)
  - `run_sql(sql: str) -> pd.DataFrame`: SQL 쿼리 실행 및 결과 반환 (abstractmethod)
  - `close() -> None`: 데이터베이스 연결 종료 (abstractmethod)

**사용처:**
- 모든 구체적인 DB 커넥터 클래스들이 이 클래스를 상속받음
- `utils.databases.connector.*` 모듈들에서 import되어 사용됨

### clickhouse_connector.py

ClickHouse 데이터베이스 연결 및 SQL 실행을 담당하는 모듈입니다.

**클래스:**
- `ClickHouseConnector(BaseConnector)`: ClickHouse 서버 연결을 위한 커넥터
  - `client`: ClickHouse Client 객체
  - `__init__(config: DBConfig)`: 호스트, 포트, 사용자, 비밀번호, 데이터베이스 설정으로 초기화
  - `connect() -> None`: clickhouse_driver.Client로 ClickHouse 서버 연결
  - `run_sql(sql: str) -> pd.DataFrame`: 쿼리 실행 후 DataFrame 반환
  - `close() -> None`: 클라이언트 연결 해제

**의존성:**
- `clickhouse_driver`
- `utils.databases.config.DBConfig`
- `utils.databases.logger.logger`

### databricks_connector.py

Databricks SQL Warehouse 연결 및 SQL 실행을 담당하는 모듈입니다.

**클래스:**
- `DatabricksConnector(BaseConnector)`: Databricks SQL Warehouse 연결을 위한 커넥터
  - `connection`: Databricks 연결 객체
  - `__init__(config: DBConfig)`: 
    - 필수 설정: host, extra.http_path, extra.access_token
    - 선택 설정: extra.catalog, extra.schema
  - `connect() -> None`: databricks.sql 모듈로 연결 설정
  - `run_sql(sql: str) -> pd.DataFrame`: 커서를 사용해 쿼리 실행 후 DataFrame 반환
  - `close() -> None`: 연결 종료

**의존성:**
- `databricks.sql`
- `utils.databases.config.DBConfig`
- `utils.databases.logger.logger`

### duckdb_connector.py

DuckDB 데이터베이스 연결 및 SQL 실행을 담당하는 모듈입니다.

**클래스:**
- `DuckDBConnector(BaseConnector)`: DuckDB 연결을 위한 커넥터
  - `connection`: DuckDB 연결 객체
  - `__init__(config: DBConfig)`: path 설정 (기본값: ":memory:")
  - `connect() -> None`: duckdb.connect로 데이터베이스 연결
  - `run_sql(sql: str) -> pd.DataFrame`: execute().fetchdf()로 DataFrame 반환
  - `close() -> None`: 연결 종료

**의존성:**
- `duckdb`
- `utils.databases.config.DBConfig`
- `utils.databases.logger.logger`

### mariadb_connector.py

MariaDB 데이터베이스 연결 및 SQL 실행을 담당하는 모듈입니다.

**클래스:**
- `MariaDBConnector(BaseConnector)`: MariaDB 서버 연결을 위한 커넥터
  - `connection`: MariaDB 연결 객체
  - `__init__(config: DBConfig)`: 호스트, 포트(기본: 3306), 사용자, 비밀번호, 데이터베이스 설정
  - `connect() -> None`: mysql.connector로 MariaDB 서버 연결
  - `run_sql(sql: str) -> pd.DataFrame`: 커서를 사용해 쿼리 실행 후 DataFrame 반환
  - `close() -> None`: 연결 종료

**의존성:**
- `mysql.connector`
- `utils.databases.config.DBConfig`
- `utils.databases.logger.logger`

### mysql_connector.py

MySQL 데이터베이스 연결 및 SQL 실행을 담당하는 모듈입니다.

**클래스:**
- `MySQLConnector(BaseConnector)`: MySQL 서버 연결을 위한 커넥터
  - `connection`: MySQL 연결 객체
  - `__init__(config: DBConfig)`: 호스트, 포트(기본: 3306), 사용자, 비밀번호, 데이터베이스 설정
  - `connect() -> None`: mysql.connector로 MySQL 서버 연결
  - `run_sql(sql: str) -> pd.DataFrame`: 커서를 사용해 쿼리 실행 후 DataFrame 반환
  - `close() -> None`: 연결 종료

**의존성:**
- `mysql.connector`
- `utils.databases.config.DBConfig`
- `utils.databases.logger.logger`

### oracle_connector.py

Oracle 데이터베이스 연결 및 SQL 실행을 담당하는 모듈입니다.

**클래스:**
- `OracleConnector(BaseConnector)`: Oracle 서버 연결을 위한 커넥터
  - `connection`: Oracle 연결 객체
  - `__init__(config: DBConfig)`:
    - 필수 설정: host, port, user, password
    - 선택 설정: extra.service_name (기본값: "orcl")
  - `connect() -> None`: oracledb.connect로 DSN 형식으로 연결
  - `run_sql(sql: str) -> pd.DataFrame`: 커서를 사용해 쿼리 실행 후 DataFrame 반환
  - `close() -> None`: 연결 종료

**의존성:**
- `oracledb`
- `utils.databases.config.DBConfig`
- `utils.databases.logger.logger`

### postgres_connector.py

PostgreSQL 데이터베이스 연결 및 SQL 실행을 담당하는 모듈입니다.

**클래스:**
- `PostgresConnector(BaseConnector)`: PostgreSQL 서버 연결을 위한 커넥터
  - `connection`: PostgreSQL 연결 객체
  - `__init__(config: DBConfig)`: 호스트, 포트, 사용자, 비밀번호, 데이터베이스 설정
  - `connect() -> None`: psycopg2.connect로 PostgreSQL 서버 연결
  - `run_sql(sql: str) -> pd.DataFrame`: 커서를 사용해 쿼리 실행 후 DataFrame 반환
  - `close() -> None`: 연결 종료

**의존성:**
- `psycopg2`
- `utils.databases.config.DBConfig`
- `utils.databases.logger.logger`

### snowflake_connector.py

Snowflake 데이터베이스 연결 및 SQL 실행을 담당하는 모듈입니다.

**클래스:**
- `SnowflakeConnector(BaseConnector)`: Snowflake 서버 연결을 위한 커넥터
  - `connection`: Snowflake 연결 객체
  - `cursor`: Snowflake 커서 객체
  - `__init__(config: DBConfig)`:
    - 필수 설정: user, password, extra.account
    - 선택 설정: extra.warehouse, database, extra.schema
  - `connect() -> None`: snowflake.connector로 연결 및 커서 생성
  - `run_sql(sql: str) -> pd.DataFrame`: 커서를 사용해 쿼리 실행 후 DataFrame 반환
  - `close() -> None`: 연결 종료

**의존성:**
- `snowflake.connector`
- `utils.databases.config.DBConfig`
- `utils.databases.logger.logger`

### sqlite_connector.py

SQLite 데이터베이스 연결 및 SQL 실행을 담당하는 모듈입니다.

**클래스:**
- `SQLiteConnector(BaseConnector)`: SQLite 파일 또는 인메모리 데이터베이스 연결을 위한 커넥터
  - `connection`: SQLite 연결 객체
  - `__init__(config: DBConfig)`: path 설정 (None 또는 ":memory:"인 경우 인메모리 DB)
  - `connect() -> None`: sqlite3.connect로 데이터베이스 연결
  - `run_sql(sql: str) -> pd.DataFrame`: 커서를 사용해 쿼리 실행 후 DataFrame 반환
  - `close() -> None`: 연결 종료

**의존성:**
- `sqlite3` (Python 표준 라이브러리)
- `utils.databases.config.DBConfig`
- `utils.databases.logger.logger`

### trino_connector.py

Trino 클러스터 연결 및 SQL 실행을 담당하는 모듈입니다.

**클래스:**
- `TrinoConnector(BaseConnector)`: Trino 클러스터 연결을 위한 커넥터
  - `connection`: Trino 연결 객체
  - `__init__(config: DBConfig)`:
    - 필수 설정: host, port
    - 선택 설정: user, password, database, extra.catalog, extra.schema, extra.http_scheme
    - database가 "catalog.schema" 형태일 경우 자동 분리
  - `connect() -> None`: trino.dbapi.connect로 연결 설정
  - `run_sql(sql: str) -> pd.DataFrame`: 커서를 사용해 쿼리 실행 후 DataFrame 반환
  - `close() -> None`: 연결 종료

**의존성:**
- `trino` (런타임에 동적으로 로드)
- `utils.databases.config.DBConfig`
- `utils.databases.logger.logger`

## 사용 방법

### 직접 사용

각 커넥터 클래스를 직접 인스턴스화하여 사용할 수 있습니다:

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
result = connector.run_sql("SELECT * FROM users")
print(result)
connector.close()
```

### Factory 패턴 사용 (권장)

`DatabaseFactory`를 사용하여 DB 타입에 따라 자동으로 적절한 커넥터를 선택할 수 있습니다:

```python
from utils.databases import DatabaseFactory

# 환경 변수 사용
connector = DatabaseFactory.get_connector()
result = connector.run_sql("SELECT * FROM users")
connector.close()

# 명시적 설정
config = DBConfig(
    host="localhost",
    port=5432,
    user="myuser",
    password="mypassword",
    database="mydb",
    extra={}
)
connector = DatabaseFactory.get_connector(db_type="postgres", config=config)
result = connector.run_sql("SELECT * FROM users")
connector.close()
```

### 지원되는 데이터베이스 타입

다음 데이터베이스들이 지원됩니다:

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

## 공통 인터페이스

모든 커넥터는 `BaseConnector` 추상 클래스를 상속받아 다음과 같은 공통 인터페이스를 구현합니다:

- `connect() -> None`: 데이터베이스에 연결
- `run_sql(sql: str) -> pd.DataFrame`: SQL 쿼리 실행 및 결과를 pandas DataFrame으로 반환
- `close() -> None`: 데이터베이스 연결 종료

## 로깅

모든 커넥터는 `utils.databases.logger`를 사용하여 연결 성공/실패 및 SQL 실행 결과를 로깅합니다.

## 에러 처리

- 연결 실패 시: `ConnectionError` 발생
- SQL 실행 실패 시: `RuntimeError` 발생
- 지원되지 않는 DB 타입: `ValueError` 발생
