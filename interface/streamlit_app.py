"""
Streamlit 애플리케이션 메인 실행 모듈.

이 모듈은 Lang2SQL 데이터 분석 도구의 내비게이션을 정의하고,
각 페이지를 연결하여 사용자가 원하는 기능을 선택할 수 있도록 합니다.

Example:
    $ streamlit run interface/streamlit_app.py
"""

import streamlit as st

st.set_page_config(
    page_title="Lang2SQL 데이터 분석 도구",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded",
)

PAGES = [
    st.Page("app_pages/home.py", title="🏠 홈"),
    st.Page("app_pages/lang2sql.py", title="🔍 Lang2SQL"),
    st.Page("app_pages/graph_builder.py", title="📊 그래프 빌더"),
]

pg = st.navigation(PAGES)
pg.run()
