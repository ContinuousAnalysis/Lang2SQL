"""
Trino 데이터베이스 커넥터 모듈.

이 모듈은 Trino 클러스터에 연결하여 SQL 쿼리를 실행하고,
그 결과를 pandas DataFrame 형태로 반환하는 기능을 제공합니다.
"""

import pandas as pd

from utils.databases.config import DBConfig
from utils.databases.connector.base_connector import BaseConnector
from utils.databases.logger import logger


class TrinoConnector(BaseConnector):
    """
    Trino 데이터베이스 커넥터 클래스.

    Trino 클러스터에 연결하여 SQL 쿼리를 실행하거나
    연결을 종료하는 기능을 제공합니다.
    """

    connection = None

    def __init__(self, config: DBConfig):
        """
        TrinoConnector 인스턴스를 초기화합니다.

        Args:
            config (DBConfig): Trino 연결 정보를 담은 설정 객체.
                - 필수 키: host, port
                - 선택 키: user, password, database, extra.catalog, extra.schema, extra.http_scheme
                - database가 "catalog.schema" 형태일 경우 자동으로 분리되어 설정됩니다.
        """
        # pylint: disable=import-outside-toplevel
        try:
            import trino

            self.trino = trino
        except ImportError as e:
            logger.error(
                "Trino 드라이버가 설치되어 있지 않습니다. pip install trino 명령을 실행하세요."
            )
            raise ImportError("Trino 라이브러리가 설치되어 있지 않습니다.") from e

        self.host = config["host"]
        self.port = config["port"] or 8080
        self.user = config.get("user") or "anonymous"
        self.password = config.get("password")
        self.database = config.get("database")  # e.g., catalog.schema
        self.extra = config.get("extra") or {}
        self.http_scheme = self.extra.get("http_scheme", "http")
        self.catalog = self.extra.get("catalog")
        self.schema = self.extra.get("schema")

        # If database given as "catalog.schema", split into fields
        if self.database and (not self.catalog or not self.schema):
            if "." in self.database:
                db_catalog, db_schema = self.database.split(".", 1)
                self.catalog = self.catalog or db_catalog
                self.schema = self.schema or db_schema

        self.connect()

    def connect(self) -> None:
        """
        Trino 클러스터에 연결을 설정합니다.

        Raises:
            ImportError: trino 드라이버를 불러오지 못한 경우 발생합니다.
            ConnectionError: Trino 서버 연결에 실패한 경우 발생합니다.
        """
        try:
            auth = None
            if self.password and self.http_scheme == "https":
                auth = self.trino.auth.BasicAuthentication(self.user, self.password)

            self.connection = self.trino.dbapi.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                http_scheme=self.http_scheme,
                catalog=self.catalog,
                schema=self.schema,
                auth=auth,
            )
            logger.info("Successfully connected to Trino.")
        except Exception as e:
            logger.error("Failed to connect to Trino: %s", e)
            raise

    def run_sql(self, sql: str) -> pd.DataFrame:
        """
        SQL 쿼리를 실행하고 결과를 pandas DataFrame으로 반환합니다.

        Args:
            sql (str): 실행할 SQL 쿼리 문자열.

        Returns:
            pd.DataFrame: 쿼리 결과를 담은 DataFrame 객체.

        Raises:
            RuntimeError: SQL 실행 중 오류가 발생한 경우.
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute(sql)
            columns = (
                [desc[0] for desc in cursor.description] if cursor.description else []
            )
            rows = cursor.fetchall() if cursor.description else []
            return pd.DataFrame(rows, columns=columns)
        except Exception as e:
            logger.error("Failed to execute SQL query on Trino: %s", e)
            raise
        finally:
            try:
                cursor.close()
            except e:
                logger.error("Failed to close cursor: %s", e)

    def close(self) -> None:
        """
        Trino 클러스터와의 연결을 종료합니다.

        연결이 존재할 경우 안전하게 닫고 리소스를 해제합니다.
        """
        if self.connection:
            self.connection.close()
            logger.info("Connection to Trino closed.")
        self.connection = None
