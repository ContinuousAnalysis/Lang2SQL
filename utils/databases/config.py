"""
데이터베이스 설정 정보를 정의하는 모듈.

이 모듈은 데이터베이스 연결에 필요한 기본 설정값과
추가 옵션(extra)을 포함한 타입 힌트를 제공합니다.
"""

from typing import Dict, Optional, TypedDict


class DBConfig(TypedDict):
    """
    데이터베이스 연결 설정 정보를 표현하는 타입 딕셔너리.

    데이터베이스 커넥터가 공통적으로 사용하는 설정 필드를 정의합니다.
    일부 필드는 선택적으로 제공될 수 있습니다.

    Attributes:
        host (str): 데이터베이스 호스트명 또는 IP 주소.
        port (Optional[int]): 데이터베이스 포트 번호.
        user (Optional[str]): 접속 사용자명.
        password (Optional[str]): 접속 비밀번호.
        database (Optional[str]): 대상 데이터베이스 이름.
        extra (Optional[Dict[str, str]]): 드라이버별 추가 설정값.
    """

    host: str
    port: Optional[int]
    user: Optional[str]
    password: Optional[str]
    database: Optional[str]
    extra: Optional[Dict[str, str]]
