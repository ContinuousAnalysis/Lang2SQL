"""
데이터베이스 커넥터의 기본 인터페이스 정의 모듈.

이 모듈은 모든 DB 커넥터 클래스가 상속해야 하는
공통 추상 클래스(BaseConnector)를 제공합니다.
"""

from abc import ABC, abstractmethod

import pandas as pd


class BaseConnector(ABC):
    """
    데이터베이스 커넥터의 기본 추상 클래스.

    모든 구체적인 DB 커넥터(Postgres, MySQL 등)는
    이 클래스를 상속받아 공통 메서드(`connect`, `run_sql`, `close`)를 구현해야 합니다.

    Attributes:
        connection (Any): DB 연결 객체. 구체 클래스에서 초기화 및 관리됩니다.
    """

    connection = None

    @abstractmethod
    def connect(self):
        """
        데이터베이스 연결을 수행합니다.

        이 메서드는 각 DB별 커넥터에서 구체적으로 구현되어야 합니다.
        """
        pass

    @abstractmethod
    def run_sql(self, sql: str) -> pd.DataFrame:
        """
        SQL 쿼리를 실행하고 결과를 반환합니다.

        Args:
            sql (str): 실행할 SQL 쿼리 문자열.

        Returns:
            pd.DataFrame: 쿼리 결과를 포함하는 데이터프레임.
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """
        데이터베이스 연결을 종료합니다.

        모든 리소스(커서, 연결 등)를 안전하게 해제해야 합니다.

        Raises:
            RuntimeError: 연결 종료 중 예외가 발생한 경우.
        """
        pass
