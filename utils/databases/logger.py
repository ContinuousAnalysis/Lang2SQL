"""
로깅 설정 모듈.

이 모듈은 애플리케이션 전역에서 사용할 기본 로깅 설정을 정의하고,
표준 로거 인스턴스(logger)를 제공합니다.
"""

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)
