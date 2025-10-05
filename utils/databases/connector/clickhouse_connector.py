"""
ClickHouse 데이터베이스 커넥터 모듈.

이 모듈은 ClickHouse 서버에 연결하여 SQL 쿼리를 실행하고,
그 결과를 pandas DataFrame 형태로 반환하는 기능을 제공합니다.
"""

import pandas as pd
from clickhouse_driver import Client

from utils.databases.config import DBConfig
from utils.databases.connector.base_connector import BaseConnector
from utils.databases.logger import logger


class ClickHouseConnector(BaseConnector):
    """
    ClickHouse 데이터베이스 커넥터 클래스.

    ClickHouse 서버에 연결하고 SQL 쿼리를 실행하거나 연결을 종료하는 기능을 제공합니다.
    """

    client = None

    def __init__(self, config: DBConfig):
        """
        ClickHouseConnector 인스턴스를 초기화합니다.

        Args:
            config (DBConfig): ClickHouse 연결 설정 정보를 담은 객체.
        """
        self.host = config["host"]
        self.port = config["port"]
        self.user = config["user"]
        self.password = config["password"]
        self.database = config["database"]
        self.connect()

    def connect(self) -> None:
        """
        ClickHouse 서버에 연결을 설정합니다.

        Raises:
            ConnectionError: 서버 연결에 실패한 경우 발생합니다.
        """
        try:
            self.client = Client(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
            )
            logger.info("Successfully connected to ClickHouse.")
        except Exception as e:
            logger.error("Failed to connect to ClickHouse: %s", e)
            raise

    def run_sql(self, sql: str) -> pd.DataFrame:
        """
        SQL 쿼리를 실행하고 결과를 DataFrame으로 반환합니다.

        Args:
            sql (str): 실행할 SQL 쿼리 문자열.

        Returns:
            pd.DataFrame: 쿼리 결과를 담은 DataFrame 객체.

        Raises:
            RuntimeError: SQL 실행 중 오류가 발생한 경우.
        """
        if self.client is None:
            self.connect()

        try:
            result = self.client.query_dataframe(sql)
            return result
        except Exception as e:
            logger.error("Failed to execute SQL query: %s", e)
            raise

    def close(self) -> None:
        """
        ClickHouse 서버와의 연결을 종료합니다.

        연결이 존재할 경우 안전하게 닫고 리소스를 해제합니다.
        """
        if self.client:
            self.client.disconnect()
            logger.info("Connection to ClickHouse closed.")
        self.client = None
