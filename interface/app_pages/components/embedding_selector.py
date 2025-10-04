import os
import streamlit as st

from interface.core.config import update_embedding_settings
from interface.app_pages.settings_sections.llm_section import LLM_PROVIDERS


def render_sidebar_embedding_selector() -> None:
    st.sidebar.markdown("### Embeddings 선택")

    default_emb = (
        (
            st.session_state.get("EMBEDDING_PROVIDER")
            or os.getenv("EMBEDDING_PROVIDER")
            or "openai"
        )
    ).lower()
    try:
        default_idx = LLM_PROVIDERS.index(default_emb)
    except ValueError:
        default_idx = 0

    selected = st.sidebar.selectbox(
        "Embeddings 공급자",
        options=LLM_PROVIDERS,
        index=default_idx,
        key="sidebar_embedding_provider",
    )

    if selected != default_emb:
        try:
            update_embedding_settings(provider=selected, values={})
            st.sidebar.success(f"Embeddings 공급자가 '{selected}'로 변경되었습니다.")
        except Exception as e:
            st.sidebar.error(f"Embeddings 공급자 변경 실패: {e}")
