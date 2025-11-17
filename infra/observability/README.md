# observability

LLM 응답 메시지에서 토큰 사용량을 집계하고 관찰(observability)하기 위한 유틸리티 모듈을 제공하는 디렉토리입니다.

## 디렉토리 구조

```
observability/
├── __pycache__/
└── token_usage.py
```

## 파일 설명

### token_usage.py

LLM 응답 메시지에서 토큰 사용량을 집계하기 위한 유틸리티 모듈입니다.

#### 주요 내용

- **TokenUtils 클래스**: LLM 토큰 사용량 집계 유틸리티 클래스
  - `get_token_usage_summary()`: 메시지 데이터에서 input/output/total 토큰 사용량을 각각 집계하는 정적 메서드
  - `usage_metadata` 필드를 기반으로 입력 토큰, 출력 토큰, 총 토큰 사용량을 계산
  - Streamlit, LangChain 등 LLM 응답을 다루는 애플리케이션에서 비용 분석, 사용량 추적 등에 활용 가능

#### 반환 형식

```python
{
    "input_tokens": int,
    "output_tokens": int,
    "total_tokens": int
}
```

## 사용 방법

### Import

이 모듈은 다음과 같이 import되어 사용됩니다:

```python
from infra.observability.token_usage import TokenUtils
```

### 실제 사용 예시

#### 1. interface/core/result_renderer.py

`TokenUtils`는 Lang2SQL 결과 표시 모듈에서 토큰 사용량을 계산하고 Streamlit UI에 표시하는 데 사용됩니다.

```75:85:interface/core/result_renderer.py
    if should_show("show_token_usage"):
        st.markdown("---")
        token_summary = TokenUtils.get_token_usage_summary(data=res["messages"])
        st.write("**토큰 사용량:**")
        st.markdown(
            f"""
            - Input tokens: `{token_summary['input_tokens']}`
            - Output tokens: `{token_summary['output_tokens']}`
            - Total tokens: `{token_summary['total_tokens']}`
            """
        )
```

**사용 컨텍스트**:
- `display_result()` 함수 내에서 LLM 실행 결과(`res`)의 `messages` 리스트를 전달받아 토큰 사용량을 집계
- Streamlit UI에서 토큰 사용량 정보를 마크다운 형식으로 표시
- 사용자가 설정에서 토큰 사용량 표시 옵션(`show_token_usage`)을 활성화한 경우에만 표시

**입력 데이터 형식**:
- `data` 파라미터는 각 항목이 `usage_metadata` 속성을 포함할 수 있는 객체 리스트입니다
- 예: LangChain의 `AIMessage` 객체 리스트

#### 사용 패턴

```python
# 기본 사용법
token_summary = TokenUtils.get_token_usage_summary(data=messages)

# 반환된 딕셔너리 접근
input_tokens = token_summary["input_tokens"]
output_tokens = token_summary["output_tokens"]
total_tokens = token_summary["total_tokens"]
```

## 로깅

이 모듈은 Python 표준 `logging` 모듈을 사용하여 토큰 사용량 정보를 기록합니다:

- **DEBUG 레벨**: 각 메시지별 토큰 사용량 상세 정보
- **INFO 레벨**: 전체 토큰 사용량 요약 정보

## 참고사항

- `usage_metadata` 필드가 없는 객체는 토큰 사용량이 0으로 처리됩니다
- 각 메시지의 토큰 사용량은 누적되어 최종 합계를 반환합니다

