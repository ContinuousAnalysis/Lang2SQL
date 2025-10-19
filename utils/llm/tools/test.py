"""
LangGraph ChatBot에서 사용하는 도구(Tool) 함수들
"""

from langchain_core.tools import tool


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
