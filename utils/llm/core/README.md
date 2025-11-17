# core

LLM(Large Language Model)과 Embedding 모델을 생성하는 팩토리 패턴을 구현한 모듈입니다. 환경변수를 통해 다양한 제공자(OpenAI, Azure, Bedrock, Gemini, Ollama, HuggingFace)의 LLM과 Embedding 모델을 통일된 인터페이스로 사용할 수 있도록 합니다.

## 디렉토리 구조

```
core/
├── __init__.py
├── factory.py
└── README.md
```

## 파일 설명

### `__init__.py`
core 모듈의 공개 인터페이스를 정의합니다.

**주요 내보내기:**
- **LLM 팩토리 함수들:**
  - `get_llm`: 환경변수(`LLM_PROVIDER`)에 따라 적절한 LLM 제공자를 선택하여 반환
  - `get_llm_openai`: OpenAI LLM 인스턴스 생성
  - `get_llm_azure`: Azure OpenAI LLM 인스턴스 생성
  - `get_llm_bedrock`: AWS Bedrock LLM 인스턴스 생성
  - `get_llm_gemini`: Google Gemini LLM 인스턴스 생성
  - `get_llm_ollama`: Ollama LLM 인스턴스 생성
  - `get_llm_huggingface`: HuggingFace LLM 인스턴스 생성

- **Embedding 팩토리 함수들:**
  - `get_embeddings`: 환경변수(`EMBEDDING_PROVIDER`)에 따라 적절한 Embedding 제공자를 선택하여 반환
  - `get_embeddings_openai`: OpenAI Embedding 인스턴스 생성
  - `get_embeddings_azure`: Azure OpenAI Embedding 인스턴스 생성
  - `get_embeddings_bedrock`: AWS Bedrock Embedding 인스턴스 생성
  - `get_embeddings_gemini`: Google Gemini Embedding 인스턴스 생성
  - `get_embeddings_ollama`: Ollama Embedding 인스턴스 생성
  - `get_embeddings_huggingface`: HuggingFace Embedding 인스턴스 생성

### `factory.py`
LLM과 Embedding 모델을 생성하는 팩토리 함수들의 구현을 포함합니다.

**주요 내용:**

#### LLM 팩토리 함수들

- **`get_llm(**kwargs) -> BaseLanguageModel`**
  - 환경변수 `LLM_PROVIDER`를 확인하여 적절한 LLM 제공자를 선택합니다.
  - 지원하는 제공자: `openai`, `azure`, `bedrock`, `gemini`, `ollama`, `huggingface`
  - 각 제공자별 전용 함수를 호출하여 LLM 인스턴스를 반환합니다.

- **제공자별 LLM 생성 함수들:**
  - `get_llm_openai(**kwargs)`: `ChatOpenAI` 인스턴스 생성
    - 환경변수: `OPEN_AI_LLM_MODEL`, `OPEN_AI_KEY`
  - `get_llm_azure(**kwargs)`: `AzureChatOpenAI` 인스턴스 생성
    - 환경변수: `AZURE_OPENAI_LLM_KEY`, `AZURE_OPENAI_LLM_ENDPOINT`, `AZURE_OPENAI_LLM_MODEL`, `AZURE_OPENAI_LLM_API_VERSION`
  - `get_llm_bedrock(**kwargs)`: `ChatBedrockConverse` 인스턴스 생성
    - 환경변수: `AWS_BEDROCK_LLM_MODEL`, `AWS_BEDROCK_LLM_ACCESS_KEY_ID`, `AWS_BEDROCK_LLM_SECRET_ACCESS_KEY`, `AWS_BEDROCK_LLM_REGION`
  - `get_llm_gemini(**kwargs)`: `ChatGoogleGenerativeAI` 인스턴스 생성
    - 환경변수: `GEMINI_LLM_MODEL`
  - `get_llm_ollama(**kwargs)`: `ChatOllama` 인스턴스 생성
    - 환경변수: `OLLAMA_LLM_MODEL`, `OLLAMA_LLM_BASE_URL` (선택적)
  - `get_llm_huggingface(**kwargs)`: `ChatHuggingFace` 인스턴스 생성
    - 환경변수: `HUGGING_FACE_LLM_MODEL`, `HUGGING_FACE_LLM_REPO_ID`, `HUGGING_FACE_LLM_ENDPOINT`, `HUGGING_FACE_LLM_API_TOKEN`

#### Embedding 팩토리 함수들

- **`get_embeddings() -> Optional[BaseLanguageModel]`**
  - 환경변수 `EMBEDDING_PROVIDER`를 확인하여 적절한 Embedding 제공자를 선택합니다.
  - 지원하는 제공자: `openai`, `azure`, `bedrock`, `gemini`, `ollama`, `huggingface`
  - 각 제공자별 전용 함수를 호출하여 Embedding 인스턴스를 반환합니다.

- **제공자별 Embedding 생성 함수들:**
  - `get_embeddings_openai()`: `OpenAIEmbeddings` 인스턴스 생성
    - 환경변수: `OPEN_AI_EMBEDDING_MODEL`, `OPEN_AI_KEY`
  - `get_embeddings_azure()`: `AzureOpenAIEmbeddings` 인스턴스 생성
    - 환경변수: `AZURE_OPENAI_EMBEDDING_KEY`, `AZURE_OPENAI_EMBEDDING_ENDPOINT`, `AZURE_OPENAI_EMBEDDING_MODEL`, `AZURE_OPENAI_EMBEDDING_API_VERSION`
  - `get_embeddings_bedrock()`: `BedrockEmbeddings` 인스턴스 생성
    - 환경변수: `AWS_BEDROCK_EMBEDDING_MODEL`, `AWS_BEDROCK_EMBEDDING_ACCESS_KEY_ID`, `AWS_BEDROCK_EMBEDDING_SECRET_ACCESS_KEY`, `AWS_BEDROCK_EMBEDDING_REGION`
  - `get_embeddings_gemini()`: `GoogleGenerativeAIEmbeddings` 인스턴스 생성
    - 환경변수: `GEMINI_EMBEDDING_MODEL`, `GEMINI_EMBEDDING_KEY`
  - `get_embeddings_ollama()`: `OllamaEmbeddings` 인스턴스 생성
    - 환경변수: `OLLAMA_EMBEDDING_MODEL`, `OLLAMA_EMBEDDING_BASE_URL`
  - `get_embeddings_huggingface()`: `HuggingFaceEndpointEmbeddings` 인스턴스 생성
    - 환경변수: `HUGGING_FACE_EMBEDDING_MODEL`, `HUGGING_FACE_EMBEDDING_REPO_ID`, `HUGGING_FACE_EMBEDDING_API_TOKEN`

## 사용 방법

### 1. `utils/llm/chains.py`에서의 사용

LangChain 체인을 생성할 때 LLM 인스턴스를 가져옵니다:

```python
from utils.llm.core import get_llm

# 환경변수 LLM_PROVIDER에 따라 적절한 LLM 반환
llm = get_llm()

# 체인 생성 시 사용
chain = prompt | llm | output_parser
```

**사용 위치:** `/home/dwlee/Lang2SQL/utils/llm/chains.py`의 모듈 레벨에서 `llm = get_llm()`로 전역 LLM 인스턴스 생성

**사용되는 체인:**
- Query Maker Chain
- Query Enrichment Chain
- Profile Extraction Chain
- Question Gate Chain
- Document Suitability Chain

### 2. `utils/llm/vectordb/faiss_db.py`에서의 사용

FAISS 벡터 데이터베이스를 생성하거나 로드할 때 Embedding 모델을 가져옵니다:

```python
from utils.llm.core import get_embeddings

# 환경변수 EMBEDDING_PROVIDER에 따라 적절한 Embedding 반환
embeddings = get_embeddings()

# FAISS 벡터 DB 생성
db = FAISS.from_documents(documents, embeddings)

# 또는 로드
db = FAISS.load_local(vectordb_path, embeddings, allow_dangerous_deserialization=True)
```

**사용 위치:** `/home/dwlee/Lang2SQL/utils/llm/vectordb/faiss_db.py`의 `get_faiss_vector_db()` 함수

### 3. `utils/llm/vectordb/pgvector_db.py`에서의 사용

PGVector 벡터 데이터베이스를 생성하거나 연결할 때 Embedding 모델을 가져옵니다:

```python
from utils.llm.core import get_embeddings

# 환경변수 EMBEDDING_PROVIDER에 따라 적절한 Embedding 반환
embeddings = get_embeddings()

# PGVector 벡터 스토어 생성
vector_store = PGVector.from_documents(
    documents=documents,
    embedding=embeddings,
    collection_name=collection_name,
    connection_string=connection_string,
)
```

**사용 위치:** `/home/dwlee/Lang2SQL/utils/llm/vectordb/pgvector_db.py`의 `get_pgvector_db()` 함수

## 환경변수 설정

이 모듈을 사용하려면 다음 환경변수들을 설정해야 합니다:

### LLM 설정

```bash
# LLM 제공자 선택 (필수)
export LLM_PROVIDER="openai"  # 또는 azure, bedrock, gemini, ollama, huggingface

# OpenAI 설정
export OPEN_AI_LLM_MODEL="gpt-4o"
export OPEN_AI_KEY="your-api-key"

# Azure OpenAI 설정
export AZURE_OPENAI_LLM_KEY="your-key"
export AZURE_OPENAI_LLM_ENDPOINT="your-endpoint"
export AZURE_OPENAI_LLM_MODEL="your-deployment-name"
export AZURE_OPENAI_LLM_API_VERSION="2023-07-01-preview"

# AWS Bedrock 설정
export AWS_BEDROCK_LLM_MODEL="anthropic.claude-3-sonnet-20240229-v1:0"
export AWS_BEDROCK_LLM_ACCESS_KEY_ID="your-access-key"
export AWS_BEDROCK_LLM_SECRET_ACCESS_KEY="your-secret-key"
export AWS_BEDROCK_LLM_REGION="us-east-1"

# Gemini 설정
export GEMINI_LLM_MODEL="gemini-pro"

# Ollama 설정
export OLLAMA_LLM_MODEL="llama2"
export OLLAMA_LLM_BASE_URL="http://localhost:11434"  # 선택적

# HuggingFace 설정
export HUGGING_FACE_LLM_MODEL="meta-llama/Llama-2-7b-chat-hf"
export HUGGING_FACE_LLM_REPO_ID="your-repo-id"
export HUGGING_FACE_LLM_ENDPOINT="your-endpoint"
export HUGGING_FACE_LLM_API_TOKEN="your-token"
```

### Embedding 설정

```bash
# Embedding 제공자 선택 (필수)
export EMBEDDING_PROVIDER="openai"  # 또는 azure, bedrock, gemini, ollama, huggingface

# OpenAI Embedding 설정
export OPEN_AI_EMBEDDING_MODEL="text-embedding-ada-002"
export OPEN_AI_KEY="your-api-key"

# Azure OpenAI Embedding 설정
export AZURE_OPENAI_EMBEDDING_KEY="your-key"
export AZURE_OPENAI_EMBEDDING_ENDPOINT="your-endpoint"
export AZURE_OPENAI_EMBEDDING_MODEL="your-deployment-name"
export AZURE_OPENAI_EMBEDDING_API_VERSION="2023-07-01-preview"

# AWS Bedrock Embedding 설정
export AWS_BEDROCK_EMBEDDING_MODEL="amazon.titan-embed-text-v1"
export AWS_BEDROCK_EMBEDDING_ACCESS_KEY_ID="your-access-key"
export AWS_BEDROCK_EMBEDDING_SECRET_ACCESS_KEY="your-secret-key"
export AWS_BEDROCK_EMBEDDING_REGION="us-east-1"

# Gemini Embedding 설정
export GEMINI_EMBEDDING_MODEL="models/embedding-001"
export GEMINI_EMBEDDING_KEY="your-api-key"

# Ollama Embedding 설정
export OLLAMA_EMBEDDING_MODEL="nomic-embed-text"
export OLLAMA_EMBEDDING_BASE_URL="http://localhost:11434"

# HuggingFace Embedding 설정
export HUGGING_FACE_EMBEDDING_MODEL="sentence-transformers/all-MiniLM-L6-v2"
export HUGGING_FACE_EMBEDDING_REPO_ID="your-repo-id"
export HUGGING_FACE_EMBEDDING_API_TOKEN="your-token"
```

## 설계 패턴

이 모듈은 **팩토리 패턴(Factory Pattern)**을 사용하여 구현되었습니다:

1. **통일된 인터페이스**: `get_llm()`과 `get_embeddings()` 함수를 통해 다양한 제공자를 동일한 방식으로 사용 가능
2. **환경변수 기반 설정**: 코드 변경 없이 환경변수만 수정하여 다른 제공자로 전환 가능
3. **확장성**: 새로운 제공자를 추가하려면 `factory.py`에 해당 제공자의 생성 함수만 추가하면 됨

## 지원하는 제공자

### LLM 제공자
- **OpenAI**: GPT 모델 시리즈
- **Azure OpenAI**: Azure에서 호스팅되는 OpenAI 모델
- **AWS Bedrock**: Claude, Llama 등 다양한 모델
- **Google Gemini**: Gemini 프로/플래시 모델
- **Ollama**: 로컬에서 실행되는 오픈소스 LLM
- **HuggingFace**: HuggingFace Hub/Endpoint를 통한 모델 접근

### Embedding 제공자
- **OpenAI**: text-embedding-ada-002 등
- **Azure OpenAI**: Azure에서 호스팅되는 OpenAI Embedding 모델
- **AWS Bedrock**: Amazon Titan Embedding 모델
- **Google Gemini**: Gemini Embedding 모델
- **Ollama**: 로컬에서 실행되는 Embedding 모델
- **HuggingFace**: HuggingFace Hub/Endpoint를 통한 Embedding 모델

