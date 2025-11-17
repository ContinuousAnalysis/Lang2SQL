## utils.visualization 개요

Lang2SQL 파이프라인에서 SQL 쿼리 결과를 시각화하기 위한 유틸리티 모듈입니다. LLM을 활용하여 적절한 차트를 자동 생성하고 Plotly를 통해 렌더링합니다.

### 파일 구조

```
utils/visualization/
└── display_chart.py    # SQL 결과를 Plotly 차트로 변환하는 핵심 모듈
```

### 각 파일 상세 설명

#### display_chart.py

**목적**: SQL 쿼리 실행 결과를 다양한 형태의 Plotly 차트로 자동 변환하는 모듈

**주요 클래스**:

- **`DisplayChart`**: SQL 결과 시각화를 담당하는 메인 클래스
  - `question` (str): 사용자가 입력한 자연어 질문
  - `sql` (str): 실행된 SQL 쿼리
  - `df_metadata` (str): 데이터프레임의 메타데이터 정보

**주요 메서드**:

1. **`llm_model_for_chart(message_log)`**
   - 환경변수 `LLM_PROVIDER`가 "openai"일 경우 ChatOpenAI로 차트 코드 생성
   - 필요 환경변수: `OPEN_AI_KEY`, `OPEN_AI_LLM_MODEL` (기본: "gpt-4o")
   - 반환: 생성된 차트 코드 또는 None

2. **`generate_plotly_code()`**
   - 사용자 질문, SQL 쿼리, 데이터프레임 메타데이터를 프롬프트로 구성
   - LLM이 데이터에 맞는 적절한 Plotly 코드 생성
   - 반환: Python 코드 문자열

3. **`get_plotly_figure(plotly_code, df, dark_mode=True)`**
   - 생성된 Plotly 코드를 실행하여 Figure 객체 생성
   - 에러 발생 시 데이터 타입 기반 fallback 차트 생성:
     - 숫자 컬럼 2개 이상 → scatter plot
     - 숫자 1개 + 범주 1개 → bar plot
     - 범주 1개 (고유값 < 10) → pie chart
     - 기타 → line plot
   - dark_mode=True 시 "plotly_dark" 템플릿 적용
   - 반환: Plotly Figure 객체 또는 None

4. **내부 헬퍼 메서드**:
   - `_extract_python_code(markdown_string)`: 마크다운에서 Python 코드 블록 추출
   - `_sanitize_plotly_code(raw_plotly_code)`: 불필요한 `fig.show()` 문 제거

**의존성**:
- `pandas`: 데이터프레임 처리
- `plotly.express` (px): 간단한 차트 생성
- `plotly.graph_objects` (go): 고급 차트 구성
- `langchain_openai.ChatOpenAI`: LLM 차트 코드 생성
- `langchain_core.messages`: SystemMessage, HumanMessage

### 사용 방법

#### 1. 기본 사용법 (interface/core/result_renderer.py에서 실제 사용)

```python
from utils.visualization.display_chart import DisplayChart
import pandas as pd

# DisplayChart 인스턴스 생성
display_code = DisplayChart(
    question="지난달 매출 추이를 보여줘",
    sql="SELECT date, revenue FROM sales WHERE ...",
    df_metadata=f"Running df.dtypes gives:\n{df.dtypes}"
)

# Plotly 코드 생성
plotly_code = display_code.generate_plotly_code()

# Figure 객체 생성
fig = display_code.get_plotly_figure(plotly_code=plotly_code, df=df)

# Streamlit에서 차트 표시
st.plotly_chart(fig)
```

#### 2. 통합 흐름 (Lang2SQL 파이프라인 내)

`interface/core/result_renderer.py`의 `display_result()` 함수에서 사용:

1. SQL 쿼리 실행 후 pandas DataFrame 반환
2. `DisplayChart` 초기화 (질문, SQL, 메타데이터)
3. `generate_plotly_code()`로 LLM 기반 차트 코드 생성
4. `get_plotly_figure()`로 실행 및 Figure 객체 획득
5. `st.plotly_chart()`로 Streamlit UI에 렌더링

**경로**: `interface/core/result_renderer.py` (200-211번째 줄)

### import 관계

**import하는 파일**:
- `interface/core/result_renderer.py`: `from utils.visualization.display_chart import DisplayChart`

**외부 의존성**:
- `langchain_openai.ChatOpenAI`: OpenAI LLM API 호출
- `plotly`: 차트 렌더링 및 Figure 객체 관리
- `pandas`: 데이터프레임 처리
- 환경변수: `LLM_PROVIDER`, `OPEN_AI_KEY`, `OPEN_AI_LLM_MODEL`

### 환경 변수 요약

- **`LLM_PROVIDER`**: LLM 공급자 지정 (현재 "openai"만 지원)
- **`OPEN_AI_KEY`**: OpenAI API 키
- **`OPEN_AI_LLM_MODEL`**: 사용할 모델 (기본값: "gpt-4o")

### 주요 특징

1. **LLM 기반 지능형 차트 생성**: 데이터 구조와 질문 내용에 맞춰 적절한 차트 유형 자동 선택
2. **Fallback 메커니즘**: LLM 코드 생성 실패 시 데이터 타입 기반 대체 차트 제공
3. **다크 모드 지원**: 기본적으로 plotly_dark 템플릿 적용
4. **에러 안전성**: 코드 실행 중 예외 발생 시에도 항상 유효한 Figure 객체 반환

### 개선 가능 영역

- 다른 LLM 공급자 지원 (현재 OpenAI만 지원)
- 더 다양한 차트 유형 지원
- 컬러 스킴 및 스타일 커스터마이징 옵션
- 성능 최적화 (코드 생성 시간 단축)

