"""ChatBot 세션 제어를 위한 사이드바 컴포넌트"""

import streamlit as st
import uuid


def render_sidebar_chatbot_session_controller() -> str:
    """ChatBot 세션 관리 및 대화 기록 표시 (사이드바 전용)

    Returns:
        str: 현재 thread_id
    """
    # 세션 ID 자동 생성 (처음 방문 시에만)
    if "chatbot_thread_id" not in st.session_state:
        st.session_state.chatbot_thread_id = str(uuid.uuid4())[:8]  # 8자리 짧은 ID

    thread_id = st.session_state.chatbot_thread_id

    # 세션 관리 섹션
    st.markdown("### 📋 세션 관리")

    # 세션 정보 표시
    st.markdown(f"**현재 세션:** `{thread_id}`")
    st.caption("대화 기록을 구분하는 고유 ID입니다.")

    # 새 세션 시작 버튼
    if st.button(
        "🔄 새 세션 시작",
        use_container_width=True,
        help="새로운 대화 세션을 시작합니다.",
    ):
        st.session_state.chatbot_thread_id = str(uuid.uuid4())[:8]
        st.session_state.chatbot_messages = []
        st.rerun()

    # 대화 기록 섹션
    if st.session_state.get("chatbot_messages"):
        st.divider()
        st.markdown("### 💬 대화 기록")

        # 메시지 개수 표시
        message_count = len(st.session_state.chatbot_messages)
        st.caption(f"총 {message_count}개의 메시지")

        # 대화 기록 표시 (접힌 상태)
        with st.expander("📄 전체 기록 보기 (JSON)", expanded=False):
            st.json(st.session_state.chatbot_messages)

        # 최근 메시지 미리보기
        if message_count > 0:
            with st.expander("👀 최근 메시지 미리보기", expanded=False):
                recent_messages = st.session_state.chatbot_messages[-3:]  # 최근 3개
                for msg in recent_messages:
                    role_icon = "👤" if msg["role"] == "user" else "🤖"
                    role_text = "사용자" if msg["role"] == "user" else "AI"
                    content_preview = (
                        msg["content"][:50] + "..."
                        if len(msg["content"]) > 50
                        else msg["content"]
                    )
                    st.caption(f"{role_icon} {role_text}: {content_preview}")

    return thread_id
