"""
Streamlit 세션 상태에서 그래프 빌더를 초기화하는 모듈.

이 모듈은 Lang2SQL 애플리케이션의 그래프 실행 파이프라인을 준비하기 위해
기본 또는 확장(enriched) 그래프 빌더를 선택적으로 로드하고,
세션 상태에 초기화된 그래프 객체를 저장합니다.

Functions:
    init_graph(use_enriched: bool) -> str:
        그래프 빌더를 초기화하고 세션 상태를 갱신합니다.
"""

import streamlit as st


def init_graph(use_enriched: bool) -> str:
    """그래프 빌더를 초기화하고 세션 상태를 갱신합니다.

    Args:
        use_enriched (bool): 확장(enriched) 그래프 빌더를 사용할지 여부.

    Returns:
        str: 초기화된 그래프 유형. "확장된" 또는 "기본".
    """

    builder_module = (
        "utils.llm.graph_utils.enriched_graph"
        if use_enriched
        else "utils.llm.graph_utils.basic_graph"
    )

    builder = __import__(builder_module, fromlist=["builder"]).builder

    st.session_state.setdefault("graph", builder.compile())
    st.session_state["graph"] = builder.compile()
    st.session_state["use_enriched"] = use_enriched

    return "확장된" if use_enriched else "기본"
