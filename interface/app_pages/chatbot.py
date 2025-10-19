"""
AI ChatBot 페이지
LangGraph와 OpenAI를 활용한 대화형 인터페이스
"""

import os
import streamlit as st

from utils.llm.chatbot import ChatBot


def initialize_session_state():
    """세션 상태 초기화 함수

    Streamlit의 session_state를 사용하여 앱의 상태를 유지합니다.
    """
    # 채팅 세션 시작 여부 플래그
    if "chatbot_started" not in st.session_state:
        st.session_state.chatbot_started = False
    # 채팅 메시지 기록 저장
    if "chatbot_messages" not in st.session_state:
        st.session_state.chatbot_messages = []

    # OpenAI API 키 확인
    openai_api_key = st.session_state.get("OPEN_AI_KEY") or os.getenv("OPEN_AI_KEY")

    if not openai_api_key:
        st.error(
            "⚠️ OpenAI API 키가 설정되지 않았습니다. 설정 > LLM에서 OpenAI API 키를 입력해주세요."
        )
        st.stop()

    # ChatBot 인스턴스 생성 (OpenAI API 키 사용)
    if "chatbot_instance" not in st.session_state:
        st.session_state.chatbot_instance = ChatBot(openai_api_key)


# 세션 상태 초기화 실행
initialize_session_state()

# 페이지 제목
st.title("🤖 AI ChatBot")

st.markdown(
    """
    LangGraph 기반 AI ChatBot과 대화를 나눌 수 있습니다.
    - 날씨 정보 조회
    - 유명한 오픈소스 프로젝트 정보
    - 일반적인 질문과 대화
    """
)

# 사이드바 UI 구성
with st.sidebar:
    st.markdown("### 🤖 ChatBot 설정")
    st.divider()

    # LLM 모델 선택 드롭다운
    selected_model = st.selectbox(
        "LLM 모델",
        options=list(ChatBot.AVAILABLE_MODELS.keys()),
        format_func=lambda x: ChatBot.AVAILABLE_MODELS[x],
        key="chatbot_model_select",
    )

    # 선택된 모델이 변경되면 ChatBot 업데이트
    if selected_model != st.session_state.chatbot_instance.model_name:
        st.session_state.chatbot_instance.update_model(selected_model)
        st.sidebar.success(
            f"모델이 '{ChatBot.AVAILABLE_MODELS[selected_model]}'로 변경되었습니다."
        )

    st.divider()

    # 채팅 세션 ID 입력 (대화 기록을 구분하는 용도)
    thread_id = st.text_input(
        "세션 ID",
        value="default",
        key="chatbot_thread_id",
        help="대화 기록을 구분하는 고유 ID입니다.",
    )

    # 채팅 세션 시작/종료 버튼
    if not st.session_state.chatbot_started:
        # 세션이 시작되지 않았을 때: 시작 버튼 표시
        if st.button("대화 시작", use_container_width=True, type="primary"):
            st.session_state.chatbot_started = True
            st.session_state.chatbot_messages = []
            st.rerun()
    else:
        # 세션이 시작되었을 때: 종료 버튼 표시
        if st.button("대화 종료", use_container_width=True):
            st.session_state.chatbot_started = False
            st.rerun()

        st.divider()

        # 세션 히스토리를 JSON 형식으로 표시 (접힌 상태)
        with st.expander("대화 기록 (JSON)", expanded=False):
            st.json(st.session_state.chatbot_messages)

# 채팅 세션이 시작된 경우에만 채팅 인터페이스 표시
if st.session_state.chatbot_started:
    # 첫 메시지가 없으면 환영 메시지 추가
    if not st.session_state.chatbot_messages:
        hello_message = "안녕하세요! 무엇을 도와드릴까요? 🤖"
        st.session_state.chatbot_messages = [
            {"role": "assistant", "content": hello_message}
        ]

    # 저장된 모든 메시지를 순서대로 표시
    for message in st.session_state.chatbot_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 사용자 입력 처리
    if prompt := st.chat_input("메시지를 입력하세요"):
        # 사용자 메시지를 기록에 추가
        st.session_state.chatbot_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # AI 응답 생성 및 표시
        with st.chat_message("assistant"):
            try:
                # ChatBot을 통해 응답 생성
                response = st.session_state.chatbot_instance.chat(prompt, thread_id)

                # 응답 내용 추출
                response_content = response["messages"][-1].content

                # 스트리밍 방식으로 응답 표시 (타이핑 효과)
                response_str = ""
                response_container = st.empty()
                for token in response_content:
                    response_str += token
                    response_container.markdown(response_str)

                # AI 응답을 기록에 추가
                st.session_state.chatbot_messages.append(
                    {"role": "assistant", "content": response_content}
                )
            except Exception as e:
                error_msg = f"오류가 발생했습니다: {str(e)}"
                st.error(error_msg)
                st.session_state.chatbot_messages.append(
                    {"role": "assistant", "content": error_msg}
                )
else:
    st.info("👈 왼쪽 사이드바에서 '대화 시작' 버튼을 눌러 ChatBot과 대화를 시작하세요!")
