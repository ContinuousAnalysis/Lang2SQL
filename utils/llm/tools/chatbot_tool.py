"""
LangGraph ChatBot에서 사용하는 도구(Tool) 함수들
"""

from langchain_core.tools import tool
from utils.llm.retrieval import search_tables
from utils.data.datahub_services.base_client import DataHubBaseClient
from utils.data.datahub_services.glossary_service import GlossaryService


@tool
def get_weather(city: str) -> str:
    """
    특정 도시의 현재 날씨 정보를 조회합니다.

    이 함수는 도시 이름을 입력받아 해당 도시의 날씨 정보를 반환합니다.
    사용자가 날씨, 기상, weather 등의 키워드와 함께 도시 이름을 언급하면 이 도구를 사용하세요.

    Args:
        city (str): 날씨를 확인하고 싶은 도시의 이름입니다.
                   예: "Seoul", "New York", "Tokyo", "서울", "부산" 등
                   영문과 한글 도시명을 모두 지원합니다.

    Returns:
        str: 해당 도시의 날씨 정보를 담은 문자열입니다.
             현재는 항상 맑은 날씨를 반환합니다.

    Examples:
        >>> get_weather("Seoul")
        'Seoul is sunny'

        >>> get_weather("서울")
        '서울 is sunny'

    Note:
        이 도구는 다음과 같은 경우에 사용하세요:
        - "서울 날씨 어때?"
        - "What's the weather in New York?"
        - "도쿄의 날씨를 알려줘"
        - "부산 날씨 확인해줘"
    """
    return f"{city} is sunny"


@tool
def get_famous_opensource() -> str:
    """
    가장 유명한 오픈소스 프로젝트를 조회합니다.

    이 함수는 현재 가장 유명한 오픈소스 프로젝트의 이름을 반환합니다.
    사용자가 유명한 오픈소스, 인기있는 오픈소스, 최고의 오픈소스 등을 물어보면 이 도구를 사용하세요.

    Returns:
        str: 가장 유명한 오픈소스 프로젝트 이름

    Examples:
        >>> get_famous_opensource()
        'Lang2SQL'

    Note:
        이 도구는 다음과 같은 경우에 사용하세요:
        - "제일 유명한 오픈소스가 뭐야?"
        - "가장 인기있는 오픈소스는?"
        - "최고의 오픈소스 프로젝트 알려줘"
        - "유명한 오픈소스 추천해줘"
    """
    return "Lang2SQL"


@tool
def search_database_tables(
    query: str, retriever_name: str = "기본", top_n: int = 5, device: str = "cpu"
) -> dict:
    """
    사용자의 자연어 쿼리를 기반으로 관련된 데이터베이스 테이블 정보를 검색합니다.

    이 함수는 SQL 쿼리 생성을 위해 필요한 테이블과 컬럼 정보를 찾아줍니다.
    사용자가 어떤 테이블을 사용해야 할지, 어떤 컬럼이 있는지 물어보거나,
    SQL 쿼리를 만들기 위한 스키마 정보가 필요할 때 이 도구를 사용하세요.

    Args:
        query (str): 검색하려는 자연어 질문입니다.
                    예: "고객 정보를 조회하려면?", "주문 관련 테이블"
        retriever_name (str, optional): 검색기 유형입니다.
                                       "기본" 또는 "Reranker" 중 선택. 기본값은 "기본"
        top_n (int, optional): 검색할 테이블 개수입니다. 기본값은 5개
        device (str, optional): 모델 실행 장치입니다. "cpu" 또는 "cuda". 기본값은 "cpu"

    Returns:
        dict: 테이블 정보가 담긴 딕셔너리입니다.
              각 테이블은 키로 저장되며, 값으로 테이블 설명과 컬럼 정보를 포함합니다.

              예시 형태:
              {
                  "customers": {
                      "table_description": "고객 정보 테이블",
                      "customer_id": "고객 고유 ID",
                      "name": "고객 이름",
                      "email": "고객 이메일"
                  },
                  "orders": {
                      "table_description": "주문 정보 테이블",
                      "order_id": "주문 ID",
                      "customer_id": "고객 ID (외래키)"
                  }
              }

    Examples:
        >>> search_database_tables("고객 정보가 필요해")
        {'customers': {'table_description': '고객 정보 테이블', ...}}

    Note:
        이 도구는 다음과 같은 경우에 사용하세요:
        - "어떤 테이블을 사용해야 해?"
        - "고객 관련 테이블 정보를 알려줘"
        - "주문 데이터는 어디에 있어?"
        - "사용 가능한 컬럼을 보여줘"
        - SQL 쿼리를 생성하기 전에 스키마 정보가 필요할 때
    """
    return search_tables(
        query=query, retriever_name=retriever_name, top_n=top_n, device=device
    )


def _simplify_glossary_data(glossary_data):
    """
    용어집 데이터를 name, description, children만 포함하는 간단한 형태로 변환

    Args:
        glossary_data: 처리된 용어집 데이터

    Returns:
        list: 간소화된 용어집 데이터 (name, description, children만 포함)
    """
    if "error" in glossary_data:
        return glossary_data

    result = []

    for node in glossary_data.get("nodes", []):
        simplified_node = {
            "name": node.get("name"),
            "description": node.get("description"),
        }

        # children 정보가 있으면 추가
        if "details" in node and "children" in node["details"]:
            children = []
            for child in node["details"]["children"]:
                child_info = {
                    "name": child.get("name"),
                    "description": child.get("description"),
                }
                children.append(child_info)

            if children:
                simplified_node["children"] = children

        result.append(simplified_node)

    return result


@tool
def get_glossary_terms(gms_server: str = "http://35.222.65.99:8080") -> list:
    """
    DataHub에서 용어집(Glossary) 정보를 조회합니다.

    이 함수는 DataHub 서버에 연결하여 전체 용어집 데이터를 가져옵니다.
    용어집은 비즈니스 용어, 도메인 지식, 데이터 정의 등을 표준화하여 관리하는 곳입니다.

    **중요**: 사용자의 질문이나 대화에서 다음과 같은 상황이 발생하면 반드시 이 도구를 사용하세요:
    1. 이해되지 않거나 모호한 단어가 나왔을 때
    2. 특정 조직이나 도메인에서 고유하게 사용되는 전문 용어가 나왔을 때
    3. 일반적이지 않은 약어나 줄임말이 나왔을 때
    4. 조직 내부에서만 통용되는 용어가 나왔을 때
    5. 표준 정의가 필요한 비즈니스 용어가 나왔을 때

    Args:
        gms_server (str, optional): DataHub GMS 서버 URL입니다.
                                   기본값은 "http://35.222.65.99:8080"

    Returns:
        list: 간소화된 용어집 데이터 리스트입니다.
              각 항목은 name, description, children(선택적) 필드를 포함합니다.

              예시 형태:
              [
                  {
                      "name": "가짜연구소",
                      "description": "스터디 단체 가짜연구소를 의미하며...",
                      "children": [
                          {
                              "name": "빌더",
                              "description": "가짜연구소 스터디 리더를 지칭..."
                          }
                      ]
                  },
                  {
                      "name": "PII",
                      "description": "개인 식별 정보...",
                      "children": [
                          {
                              "name": "identifier",
                              "description": "개인식별정보중 github 아이디..."
                          }
                      ]
                  }
              ]

    Examples:
        >>> get_glossary_terms()
        [{'name': '가짜연구소', 'description': '...', 'children': [...]}]

    Note:
        이 도구는 다음과 같은 경우에 **반드시** 사용하세요:

        [명시적 요청]
        - "용어집을 보여줘"
        - "비즈니스 용어가 뭐가 있어?"
        - "데이터 사전 정보를 알려줘"
        - "정의된 용어들을 보여줘"

        [이해되지 않는 단어 감지 - 매우 중요!]
        - 일반적이지 않은 약어나 전문 용어가 대화에 등장할 때
        - 표준 정의가 없는 도메인 특화 용어가 나올 때
        - 질문의 맥락에서 모호하거나 불명확한 용어가 있을 때

        [조직/도메인 특화 상황]
        - 특정 조직에서만 사용하는 내부 용어가 나올 때
        - 업계/도메인 전문 용어가 필요할 때
        - 데이터나 테이블 관련 비즈니스 컨텍스트를 이해하기 위해

        **핵심**: 응답하기 전에 사용자의 질문에 조직 특화 용어나 모호한 단어가
        있는지 확인하고, 있다면 먼저 이 도구를 호출하여 정확한 정의를 파악하세요.
    """
    try:
        # DataHub 클라이언트 초기화
        client = DataHubBaseClient(gms_server=gms_server)

        # GlossaryService 초기화
        glossary_service = GlossaryService(client)

        # 전체 용어집 데이터 가져오기
        glossary_data = glossary_service.get_glossary_data()

        # 간소화된 데이터 반환
        simplified_data = _simplify_glossary_data(glossary_data)

        return simplified_data

    except ValueError as e:
        return {"error": True, "message": f"DataHub 서버 연결 실패: {str(e)}"}
    except Exception as e:
        return {"error": True, "message": f"용어집 조회 중 오류 발생: {str(e)}"}
