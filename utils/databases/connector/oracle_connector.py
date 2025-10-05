"""
Oracle 데이터베이스 커넥터 모듈.

이 모듈은 Oracle 데이터베이스에 연결하여 SQL 쿼리를 실행하고,
결과를 pandas DataFrame 형태로 반환하는 기능을 제공합니다.
"""

import oracledb
import pandas as pd

from utils.databases.config import DBConfig
from utils.databases.connector.base_connector import BaseConnector
from utils.databases.logger import logger


class OracleConnector(BaseConnector):
    """
    Oracle 데이터베이스 커넥터 클래스.

    Oracle 서버에 연결하여 SQL 쿼리를 실행하거나 연결을 종료하는 기능을 제공합니다.
    """

    connection = None

    def __init__(self, config: DBConfig):
        """
        OracleConnector 인스턴스를 초기화합니다.

        Args:
            config (DBConfig): Oracle 연결 정보를 담은 설정 객체.
                - 필수 키: host, port, user, password
                - 선택 키: extra.service_name (기본값: "orcl")
        """
        self.host = config["host"]
        self.port = config["port"]
        self.user = config["user"]
        self.password = config["password"]
        self.service_name = config.get("extra").get("service_name", "orcl")
        self.connect()

    def connect(self) -> None:
        """
        Oracle 데이터베이스에 연결을 설정합니다.

        Raises:
            ConnectionError: Oracle 서버 연결에 실패한 경우 발생합니다.
        """
        try:
            self.connection = oracledb.connect(
                user=self.user,
                password=self.password,
                dsn=f"{self.host}:{self.port}/{self.service_name}",
            )
            logger.info("Successfully connected to Oracle.")
        except Exception as e:
            logger.error("Failed to connect to Oracle: %s", e)
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
        Oracle 데이터베이스 연결을 종료합니다.

        연결이 존재할 경우 안전하게 닫고 리소스를 해제합니다.
        """
        if self.connection:
            self.connection.close()
            logger.info("Connection to Oracle closed.")
        self.connection = None
