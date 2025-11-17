# output_schema 모듈

LLM 구조화 출력을 위한 Pydantic 모델 정의 모듈입니다.

## 디렉토리 구조

```
output_schema/
├── __pycache__/
├── document_suitability.py
└── question_suitability.py
```

## 파일 목록 및 설명

### document_suitability.py

**목적**: LLM 구조화 출력으로부터 테이블별 적합성 평가 결과를 표현하는 Pydantic 모델을 정의합니다.

**주요 클래스**:

- `DocumentSuitability`: 단일 테이블에 대한 적합성 평가 결과를 표현하는 모델
  - `table_name` (str): 테이블명
  - `score` (float): 0.0~1.0 사이의 적합도 점수
  - `reason` (str): 한국어 한두 문장 근거
  - `matched_columns` (List[str]): 질문과 직접 연관된 컬럼명 목록
  - `missing_entities` (List[str]): 부족한 엔티티/지표/기간 등

- `DocumentSuitabilityList`: 문서 적합성 평가 결과 리스트 래퍼
  - `results` (List[DocumentSuitability]): 평가 결과 목록
  - OpenAI Structured Outputs 호환을 위해 명시적 최상위 키(`results`)를 제공

### question_suitability.py

**목적**: LLM 구조화 출력으로부터 SQL 적합성 판단 결과를 표현하는 Pydantic 모델을 정의합니다.

**주요 클래스**:

- `QuestionSuitability`: SQL 생성 적합성 결과 모델
  - `reason` (str): 보완/설명 사유 요약
  - `missing_entities` (list[str]): 질문에서 누락된 핵심 엔터티/기간 등
  - `requires_data_science` (bool): SQL을 넘어 ML/통계 분석이 필요한지 여부

## 사용 방법

### Import 및 사용 위치

이 모듈의 클래스들은 `utils/llm/chains.py`에서 import되어 사용됩니다:

```python
from utils.llm.output_schema.document_suitability import DocumentSuitabilityList
from utils.llm.output_schema.question_suitability import QuestionSuitability
```

### 사용 예시

#### 1. QuestionSuitability 사용

`create_question_gate_chain()` 함수에서 질문 적합성을 판단하는 체인을 생성할 때 사용됩니다:

```python
def create_question_gate_chain(llm):
    """
    질문 적합성(Question Gate) 체인을 생성합니다.
    
    Returns:
        Runnable: invoke({"question": str}) -> QuestionSuitability
    """
    prompt = get_prompt_template("question_gate_prompt")
    gate_prompt = ChatPromptTemplate.from_messages(
        [SystemMessagePromptTemplate.from_template(prompt)]
    )
    return gate_prompt | llm.with_structured_output(QuestionSuitability)
```

**사용 흐름**:
1. 사용자 질문을 입력으로 받음
2. LLM이 구조화된 출력으로 `QuestionSuitability` 객체를 반환
3. SQL 생성이 적합한지 여부와 필요 보완 사항을 판단

#### 2. DocumentSuitabilityList 사용

`create_document_suitability_chain()` 함수에서 문서(테이블) 적합성을 평가하는 체인을 생성할 때 사용됩니다:

```python
def create_document_suitability_chain(llm):
    """
    문서 적합성 평가 체인을 생성합니다.
    
    Returns:
        Runnable: invoke({"question": str, "tables": dict}) -> {"results": DocumentSuitability[]}
    """
    prompt = get_prompt_template("document_suitability_prompt")
    doc_prompt = ChatPromptTemplate.from_messages(
        [SystemMessagePromptTemplate.from_template(prompt)]
    )
    return doc_prompt | llm.with_structured_output(DocumentSuitabilityList)
```

**사용 흐름**:
1. 사용자 질문과 검색된 테이블 메타데이터를 입력으로 받음
2. LLM이 각 테이블에 대한 적합도 점수와 평가 결과를 포함한 `DocumentSuitabilityList` 객체를 반환
3. 가장 적합한 테이블을 선택하거나 적합도가 낮은 경우 사용자에게 알림

### 구조화 출력 활용

두 모델 모두 LangChain의 `with_structured_output()` 메서드와 함께 사용되어 LLM의 출력을 자동으로 Pydantic 모델로 변환합니다. 이를 통해:

- 타입 안전성 보장
- 자동 검증 및 직렬화
- 명확한 API 계약

을 제공합니다.

