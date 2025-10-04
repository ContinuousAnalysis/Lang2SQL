"""
Settings 페이지 – 섹션 기반 UI
"""

import streamlit as st

from interface.core.config import load_config
from interface.app_pages.settings_sections.data_source_section import (
    render_data_source_section,
)
from interface.app_pages.settings_sections.llm_section import render_llm_section


st.title("⚙️ 설정")

config = load_config()

tabs = st.tabs(["데이터 소스", "LLM", "DB", "Device"])

with tabs[0]:
    render_data_source_section(config)

with tabs[1]:
    render_llm_section(config)

with tabs[2]:
    st.info("DB 연결 설정은 곧 제공됩니다.")

with tabs[3]:
    st.info("디바이스 설정은 곧 제공됩니다.")

st.divider()
st.caption("민감 정보는 로그에 기록되지 않으며, 이 설정은 현재 세션에 우선 반영됩니다.")
