"""
Streamlit 애플리케이션 메인 실행 모듈.

Lang2SQL 데이터 분석 도구의 내비게이션을 초기화하고 실행합니다.
"""

import streamlit as st

from interface.pages_config import PAGES


def configure_app() -> None:
    """앱 전역 설정 초기화.

    Streamlit 애플리케이션의 제목, 아이콘, 레이아웃, 사이드바 상태를 설정합니다.

    Returns:
        None
    """
    st.set_page_config(
        page_title="Lang2SQL 데이터 분석 도구",
        page_icon="🔎",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def main() -> None:
    """애플리케이션 진입점.

    전역 설정을 초기화하고, 정의된 페이지 내비게이션을 실행합니다.

    Returns:
        None
    """
    configure_app()
    pg = st.navigation(PAGES)
    pg.run()


if __name__ == "__main__":
    main()
