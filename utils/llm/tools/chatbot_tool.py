"""
LangGraph ChatBot에서 사용하는 도구(Tool) 함수들
"""

from langchain_core.tools import tool
from utils.llm.retrieval import search_tables


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
