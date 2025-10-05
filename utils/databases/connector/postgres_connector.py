"""
PostgreSQL 데이터베이스 커넥터 모듈.

이 모듈은 PostgreSQL 서버에 연결하여 SQL 쿼리를 실행하고,
결과를 pandas DataFrame 형태로 반환하는 기능을 제공합니다.
"""

import pandas as pd
import psycopg2

from utils.databases.config import DBConfig
from utils.databases.connector.base_connector import BaseConnector
from utils.databases.logger import logger


class PostgresConnector(BaseConnector):
    """
    PostgreSQL 데이터베이스 커넥터 클래스.

    PostgreSQL 서버에 연결하고 SQL 쿼리를 실행하거나 연결을 종료하는 기능을 제공합니다.
    """

    connection = None

    def __init__(self, config: DBConfig):
        """
        PostgresConnector 인스턴스를 초기화합니다.

        Args:
            config (DBConfig): PostgreSQL 연결 정보를 담은 설정 객체.
        """
        self.host = config["host"]
        self.port = config["port"]
        self.user = config["user"]
        self.password = config["password"]
        self.database = config["database"]
        self.connect()

    def connect(self) -> None:
        """
        PostgreSQL 서버에 연결합니다.

        Raises:
            ConnectionError: 서버 연결에 실패한 경우 발생합니다.
        """
        try:
            self.connection = psycopg2.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                dbname=self.database,
            )
            logger.info("Successfully connected to PostgreSQL.")
        except Exception as e:
            logger.error("Failed to connect to PostgreSQL: %s", e)
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
        PostgreSQL 서버와의 연결을 종료합니다.

        연결이 존재할 경우 안전하게 닫고 리소스를 해제합니다.
        """
        if self.connection:
            self.connection.close()
            logger.info("Connection to PostgreSQL closed.")
        self.connection = None
