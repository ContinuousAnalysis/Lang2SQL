"""Streamlit 세션 상태 유틸리티 모듈."""


def init_pipeline(use_enriched: bool) -> str:
    """파이프라인 타입을 세션 상태에 기록한다.

    Args:
        use_enriched: True이면 EnrichedNL2SQL, False이면 BaselineNL2SQL.

    Returns:
        str: "확장된" 또는 "기본".
    """
    import streamlit as st

    st.session_state["use_enriched"] = use_enriched
    return "확장된" if use_enriched else "기본"
