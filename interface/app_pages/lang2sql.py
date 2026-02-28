"""
Lang2SQL Streamlit 애플리케이션.

자연어 질의를 SQL 쿼리로 변환하고 실행 결과를 시각화하는 인터페이스를 제공합니다.

주요 기능:
    - 사용자 질의를 SQL 쿼리로 변환 후 실행
    - SQL 방언(dialect) 선택 지원
    - 쿼리 실행 결과를 표로 시각화
    - Baseline / Enriched 워크플로우 선택
"""

import pandas as pd
import streamlit as st

from interface.core.config import load_config
from interface.core.lang2sql_runner import run_lang2sql
from interface.app_pages.sidebar_components import (
    render_sidebar_data_source_selector,
    render_sidebar_db_selector,
    render_sidebar_embedding_selector,
    render_sidebar_llm_selector,
)

TITLE = "Lang2SQL"
DEFAULT_QUERY = "고객 데이터를 기반으로 유니크한 유저 수를 카운트하는 쿼리"

DIALECT_OPTIONS = ["default", "sqlite", "postgresql", "mysql", "bigquery", "duckdb"]

st.title(TITLE)

config = load_config()

render_sidebar_data_source_selector(config)
st.sidebar.divider()
render_sidebar_llm_selector()
st.sidebar.divider()
render_sidebar_embedding_selector()
st.sidebar.divider()
render_sidebar_db_selector()
st.sidebar.divider()

st.sidebar.markdown("### 워크플로우 선택")
use_enriched = st.sidebar.checkbox(
    "프로파일 추출 & 컨텍스트 보강 워크플로우 사용 (Enriched)", value=False
)

# 쿼리 입력
user_query = st.text_area("쿼리를 입력하세요:", value=DEFAULT_QUERY)

# 설정
col1, col2 = st.columns(2)
with col1:
    user_dialect = st.selectbox("SQL 방언(Dialect):", options=DIALECT_OPTIONS, index=0)
with col2:
    user_top_n = st.slider(
        "검색할 테이블 정보 개수:", min_value=1, max_value=20, value=5
    )

if st.button("쿼리 실행"):
    with st.spinner("쿼리 실행 중..."):
        res = run_lang2sql(
            query=user_query,
            db_dialect=user_dialect if user_dialect != "default" else None,
            top_n=user_top_n,
            use_enriched=use_enriched,
        )

    if res.get("error"):
        st.error(f"오류 발생: {res['error']}")
    else:
        rows = res.get("rows", [])
        if rows:
            st.success(f"{len(rows)}개 행 반환됨.")
            st.markdown("**쿼리 실행 결과:**")
            st.dataframe(pd.DataFrame(rows))
        else:
            st.info("쿼리 실행 결과가 없습니다.")
