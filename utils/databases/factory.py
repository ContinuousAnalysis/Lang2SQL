"""
데이터베이스 커넥터 팩토리 모듈.

이 모듈은 DB 타입에 따라 알맞은 커넥터 클래스를 동적으로 로드하여
해당 DB에 연결할 수 있는 인스턴스를 생성하는 기능을 제공합니다.
환경변수로부터 접속 설정을 자동으로 로드하는 유틸리티 함수도 포함합니다.
"""

import importlib
import os
from typing import Optional

from utils.databases.config import DBConfig
from utils.databases.logger import logger


class DatabaseFactory:
    """
    데이터베이스 커넥터 팩토리 클래스.

    DB 타입에 따라 알맞은 Connector 클래스를 동적으로 로드하고,
    해당 인스턴스를 반환하는 기능을 제공합니다.
    """

    @staticmethod
    def get_connector(db_type: Optional[str] = None, config: Optional[DBConfig] = None):
        """
        주어진 DB 타입에 맞는 Connector 인스턴스를 반환합니다.

        Args:
            db_type (Optional[str]): DB 타입 문자열. (예: 'postgres', 'mysql', 'trino')
            config (Optional[DBConfig]): DB 연결 설정 객체.
                지정되지 않은 경우 환경변수에서 자동 로드합니다.

        Returns:
            BaseConnector: 지정된 DB 타입에 맞는 Connector 인스턴스.

        Raises:
            ValueError: 지원되지 않는 DB 타입이거나 모듈을 로드할 수 없는 경우.
        """
        if not db_type:
            db_type = os.getenv("DB_TYPE")
            if not db_type:
                raise ValueError("DB_TYPE이 환경변수 또는 인자로 제공되어야 합니다.")
        db_type = db_type.lower()

        if not config:
            config = load_config_from_env(db_type.upper())

        try:
            module_name = f"utils.databases.connector.{db_type}_connector"
            module = importlib.import_module(module_name)
            connector_class = getattr(module, f"{db_type.capitalize()}Connector")
        except (ImportError, AttributeError) as e:
            logger.error(
                "지원되지 않는 DB 타입이거나 모듈을 로드할 수 없습니다: {%s}",
                db_type,
            )
            raise ValueError(f"Unsupported DB type: {db_type}") from e

        return connector_class(config)


def load_config_from_env(prefix: str) -> DBConfig:
    """
    환경변수에서 데이터베이스 접속 설정을 로드합니다.

    Args:
        prefix (str): 환경변수 접두어 (예: 'POSTGRES', 'MYSQL').

    Returns:
        DBConfig: 환경변수에서 로드된 설정 정보를 담은 DBConfig 객체.
    """
    base_keys = {
        "HOST",
        "PORT",
        "USER",
        "PASSWORD",
        "DATABASE",
    }
    config = {
        "host": os.getenv(f"{prefix}_HOST"),
        "port": (
            int(os.getenv(f"{prefix}_PORT")) if os.getenv(f"{prefix}_PORT") else None
        ),
        "user": os.getenv(f"{prefix}_USER"),
        "password": os.getenv(f"{prefix}_PASSWORD"),
        "database": os.getenv(f"{prefix}_DATABASE"),
    }

    extra = {}
    for key, value in os.environ.items():
        if (
            key.startswith(f"{prefix}_")
            and key.split("_", 1)[1].upper() not in base_keys
        ):
            extra[key[len(prefix) + 1 :].lower()] = value
    if extra:
        config["extra"] = extra

    return DBConfig(**config)
