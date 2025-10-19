"""
LangGraph 기반 ChatBot 모델
OpenAI의 ChatGPT 모델을 사용하여 대화 기록을 유지하는 챗봇 구현
"""

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

from utils.llm.tools import (
    get_weather,
    get_famous_opensource,
    search_database_tables,
)


class ChatBot:
    """
    LangGraph를 사용한 대화형 챗봇 클래스
    OpenAI API를 통해 다양한 GPT 모델을 사용할 수 있으며,
    MemorySaver를 통해 대화 기록을 관리합니다.
    """

    # 사용 가능한 OpenAI 모델 목록 (키: 모델ID, 값: 표시명)
    AVAILABLE_MODELS = {
        "gpt-4o": "GPT-4o",
        "gpt-4o-mini": "GPT-4o Mini",
        "gpt-4-turbo": "GPT-4 Turbo",
        "gpt-3.5-turbo": "GPT-3.5 Turbo",
    }

    def __init__(self, openai_api_key: str, model_name: str = "gpt-4o-mini"):
        """
        ChatBot 인스턴스 초기화

        Args:
            openai_api_key: OpenAI API 키
            model_name: 사용할 모델명 (기본값: gpt-4o-mini)
        """
        self.openai_api_key = openai_api_key
        self.model_name = model_name
        # SQL 생성을 위한 데이터베이스 메타데이터 조회 도구
        self.tools = [
            search_database_tables,  # 데이터베이스 테이블 정보 검색
            get_weather,  # 테스트용 도구 (추후 제거 가능)
            get_famous_opensource,  # 테스트용 도구 (추후 제거 가능)
        ]
        self.llm = self._setup_llm()  # LLM 인스턴스 설정
        self.app = self._setup_workflow()  # LangGraph 워크플로우 설정

    def _setup_llm(self):
        """
        OpenAI ChatGPT LLM 인스턴스 생성
        Tool을 바인딩하여 LLM이 필요시 tool을 호출할 수 있도록 설정합니다.

        Returns:
            ChatOpenAI: Tool이 바인딩된 LLM 인스턴스
        """
        llm = ChatOpenAI(
            temperature=0.0,  # SQL 생성은 정확성이 중요하므로 0으로 설정
            openai_api_key=self.openai_api_key,
            model_name=self.model_name,
        )
        # Tool을 LLM에 바인딩하여 함수 호출 기능 활성화
        return llm.bind_tools(self.tools)

    def _setup_workflow(self):
        """
        LangGraph 워크플로우 설정
        대화 기록을 관리하고 LLM과 통신하는 그래프 구조를 생성합니다.
        Tool 호출 기능을 포함하여 LLM이 필요시 도구를 사용할 수 있도록 합니다.

        Returns:
            CompiledGraph: 컴파일된 LangGraph 워크플로우
        """
        # MessagesState를 사용하는 StateGraph 생성
        workflow = StateGraph(state_schema=MessagesState)

        def call_model(state: MessagesState):
            """
            LLM 모델을 호출하는 노드 함수
            LLM이 응답을 생성하거나 tool 호출을 결정합니다.

            Args:
                state: 현재 메시지 상태

            Returns:
                dict: LLM 응답이 포함된 상태 업데이트
            """
            # SQL 생성 전문 어시스턴트 시스템 메시지
            sys_msg = SystemMessage(
                content="""# 역할
당신은 사용자가 SQL 쿼리를 생성하도록 돕는 전문 AI 어시스턴트입니다.

# 주요 임무
- 사용자의 자연어 질문을 이해하고 SQL 쿼리 생성에 필요한 정보를 파악합니다
- 필요한 경우 데이터베이스 스키마나 메타데이터를 확인하기 위해 도구를 활용합니다
- 단계별로 사용자와 대화하며 명확한 SQL 쿼리를 만들어갑니다
- 생성된 SQL에 대해 이해하기 쉽게 설명합니다

# 작업 프로세스
1. 사용자의 의도를 명확히 파악
2. 필요한 테이블/컬럼 정보 확인 (도구 사용)
3. 사용자의 질문을 바탕으로 정보를 추출할 수 있는 명확한 질문으로 변환합니다

# 주의사항
- 항상 친절하고 명확하게 대화합니다
- 이전 대화 맥락을 고려하여 일관성 있게 응답합니다
- 사용자가 SQL을 이해할 수 있도록 단계별로 설명합니다

---
다음은 사용자와의 대화입니다:"""
            )
            # 시스템 메시지를 대화의 맨 앞에 추가
            messages = [sys_msg] + state["messages"]
            response = self.llm.invoke(messages)
            return {"messages": response}

        def route_model_output(state: MessagesState):
            """
            LLM 출력에 따라 다음 노드를 결정하는 라우팅 함수
            Tool 호출이 필요한 경우 'tools' 노드로, 아니면 대화를 종료합니다.

            Args:
                state: 현재 메시지 상태

            Returns:
                str: 다음에 실행할 노드 이름 ('tools' 또는 '__end__')
            """
            messages = state["messages"]
            last_message = messages[-1]
            # LLM이 tool을 호출하려고 하는 경우 (tool_calls가 있는 경우)
            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                return "tools"
            # Tool 호출이 없으면 대화 종료
            return "__end__"

        # 워크플로우 구조 정의
        workflow.add_edge(START, "model")  # 시작 -> model 노드
        workflow.add_node("model", call_model)  # LLM 호출 노드
        workflow.add_node("tools", ToolNode(self.tools))  # Tool 실행 노드

        # model 노드 이후 조건부 라우팅
        workflow.add_conditional_edges("model", route_model_output)
        # Tool 실행 후 다시 model로 돌아가서 최종 응답 생성
        workflow.add_edge("tools", "model")

        # MemorySaver를 사용하여 대화 기록 저장 기능 추가
        return workflow.compile(checkpointer=MemorySaver())

    def chat(self, message: str, thread_id: str):
        """
        사용자 메시지에 대한 응답 생성

        Args:
            message: 사용자 입력 메시지
            thread_id: 대화 세션을 구분하는 고유 ID

        Returns:
            dict: LLM 응답을 포함한 결과 딕셔너리
        """
        return self.app.invoke(
            {"messages": [{"role": "user", "content": message}]},
            {"configurable": {"thread_id": thread_id}},  # thread_id로 대화 기록 관리
        )

    def update_model(self, model_name: str):
        """
        사용 중인 LLM 모델 변경
        모델 변경 시 LLM 인스턴스와 워크플로우를 재설정합니다.

        Args:
            model_name: 변경할 모델명
        """
        self.model_name = model_name
        self.llm = self._setup_llm()  # 새 모델로 LLM 재설정
        self.app = self._setup_workflow()  # 워크플로우 재생성
