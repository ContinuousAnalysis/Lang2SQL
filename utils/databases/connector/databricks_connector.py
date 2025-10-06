"""
Databricks SQL Warehouse 커넥터 모듈.

이 모듈은 Databricks SQL Warehouse에 연결하여 SQL 쿼리를 실행하고,
결과를 pandas DataFrame 형태로 반환하는 기능을 제공합니다.
"""

import pandas as pd
from databricks import sql

from utils.databases.config import DBConfig
from utils.databases.connector.base_connector import BaseConnector
from utils.databases.logger import logger


class DatabricksConnector(BaseConnector):
    """
    Databricks SQL Warehouse 커넥터 클래스.

    Databricks SQL 엔드포인트에 연결하여 쿼리를 실행하고,
    결과를 DataFrame으로 반환하는 기능을 제공합니다.
    """

    connection = None

    def __init__(self, config: DBConfig):
        """
        DatabricksConnector 인스턴스를 초기화합니다.

        Args:
            config (DBConfig): Databricks 연결 정보를 담은 설정 객체.
                - 필수 키: host, extra.http_path, extra.access_token
                - 선택 키: extra.catalog, extra.schema
        """
        self.server_hostname = config["host"]
        self.http_path = config["extra"]["http_path"]
        self.access_token = config["extra"]["access_token"]
        self.catalog = config.get("extra", {}).get("catalog")
        self.schema = config.get("extra", {}).get("schema")
        self.connect()

    def connect(self) -> None:
        """
        Databricks SQL Warehouse에 연결을 설정합니다.

        Raises:
            ConnectionError: 연결 설정 중 오류가 발생한 경우.
        """
        try:
            self.connection = sql.connect(
                server_hostname=self.server_hostname,
                http_path=self.http_path,
                access_token=self.access_token,
                catalog=self.catalog,
                schema=self.schema,
            )
            logger.info("Successfully connected to Databricks.")
        except Exception as e:
            logger.error("Failed to connect to Databricks: %s", e)
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
        if self.connection is None:
            self.connect()

        try:
            cursor = self.connection.cursor()
            cursor.execute(sql)
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            return pd.DataFrame(rows, columns=columns)
        except Exception as e:
            logger.error("Failed to execute SQL query: %s", e)
            raise
        finally:
            cursor.close()

    def close(self) -> None:
        """
        Databricks SQL Warehouse와의 연결을 종료합니다.

        연결이 존재할 경우 안전하게 닫고 리소스를 해제합니다.
        """
        if self.connection:
            self.connection.close()
            logger.info("Connection to Databricks closed.")
        self.connection = None
