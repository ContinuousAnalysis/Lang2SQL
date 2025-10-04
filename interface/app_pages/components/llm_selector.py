import os
import streamlit as st

from interface.core.config import update_llm_settings
from interface.app_pages.settings_sections.llm_section import LLM_PROVIDERS


def render_sidebar_llm_selector() -> None:
    st.sidebar.markdown("### LLM 선택")

    default_llm = (
        (st.session_state.get("LLM_PROVIDER") or os.getenv("LLM_PROVIDER") or "openai")
    ).lower()
    try:
        default_idx = LLM_PROVIDERS.index(default_llm)
    except ValueError:
        default_idx = 0

    selected = st.sidebar.selectbox(
        "LLM 공급자",
        options=LLM_PROVIDERS,
        index=default_idx,
        key="sidebar_llm_provider",
    )

    if selected != default_llm:
        try:
            update_llm_settings(provider=selected, values={})
            st.sidebar.success(f"LLM 공급자가 '{selected}'로 변경되었습니다.")
        except Exception as e:
            st.sidebar.error(f"LLM 공급자 변경 실패: {e}")
