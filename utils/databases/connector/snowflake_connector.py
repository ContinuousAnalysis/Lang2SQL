"""
Snowflake 데이터베이스 커넥터 모듈.

이 모듈은 Snowflake 데이터베이스에 연결하여 SQL 쿼리를 실행하고,
결과를 pandas DataFrame 형태로 반환하는 기능을 제공합니다.
"""

import pandas as pd
from snowflake import connector

from utils.databases.config import DBConfig
from utils.databases.connector.base_connector import BaseConnector
from utils.databases.logger import logger


class SnowflakeConnector(BaseConnector):
    """
    Snowflake 데이터베이스 커넥터 클래스.

    Snowflake 서버에 연결하여 SQL 쿼리를 실행하거나 연결을 종료하는 기능을 제공합니다.
    """

    connection = None

    def __init__(self, config: DBConfig):
        """
        SnowflakeConnector 인스턴스를 초기화합니다.

        Args:
            config (DBConfig): Snowflake 연결 정보를 담은 설정 객체.
                - 필수 키: user, password, extra.account
                - 선택 키: extra.warehouse, database, extra.schema
        """
        self.user = config["user"]
        self.password = config["password"]
        self.account = config["extra"]["account"]
        self.warehouse = config.get("extra", {}).get("warehouse")
        self.database = config.get("database")
        self.schema = config.get("extra", {}).get("schema")
        self.connect()

    def connect(self) -> None:
        """
        Snowflake 데이터베이스에 연결을 설정합니다.

        Raises:
            ConnectionError: Snowflake 서버 연결에 실패한 경우 발생합니다.
        """
        try:
            self.connection = connector.connect(
                user=self.user,
                password=self.password,
                account=self.account,
                warehouse=self.warehouse,
                database=self.database,
                schema=self.schema,
            )
            logger.info("Successfully connected to Snowflake.")
            self.cursor = self.connection.cursor()
        except Exception as e:
            logger.error("Failed to connect to Snowflake: %s", e)
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

        cursor = self.connection.cursor()

        try:
            self.cursor.execute(sql)
            columns = [col[0] for col in self.cursor.description]
            data = self.cursor.fetchall()
            return pd.DataFrame(data, columns=columns)
        except Exception as e:
            logger.error("Failed to execute SQL query: %s", e)
            raise
        finally:
            cursor.close()

    def close(self) -> None:
        """
        Snowflake 데이터베이스 연결을 종료합니다.

        연결이 존재할 경우 안전하게 닫고 리소스를 해제합니다.
        """
        if self.connection:
            self.connection.close()
            logger.info("Connection to Snowflake closed.")
        self.connection = None
