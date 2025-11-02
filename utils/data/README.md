# utils/data 패키지

DataHub와의 상호작용을 위한 데이터 관련 유틸리티 패키지입니다.

## 디렉토리 구조

```
utils/data/
├── __pycache__/
├── datahub_services/
│   ├── __pycache__/
│   ├── base_client.py           # 기본 클라이언트
│   ├── glossary_service.py      # 용어집 서비스
│   ├── metadata_service.py      # 메타데이터 서비스
│   ├── query_service.py         # 쿼리 서비스
│   ├── __init__.py              # 패키지 초기화 및 exports
│   └── README.md                # 서비스 상세 문서
├── datahub_source.py            # 통합 메타데이터 페처
└── queries.py                   # GraphQL 쿼리 모음
```

## 파일별 상세 내용

### `datahub_source.py`

DataHub 메타데이터 페처 - 리팩토링된 버전으로 기존 `DatahubMetadataFetcher`의 모든 기능을 유지하면서 내부적으로는 분리된 서비스 모듈들을 사용합니다.

**클래스:**
- `DatahubMetadataFetcher`: 기존 인터페이스를 유지하는 통합 페처

**초기화:**
```python
from utils.data.datahub_source import DatahubMetadataFetcher

fetcher = DatahubMetadataFetcher(gms_server="http://localhost:8080", extra_headers={})
```

**주요 메서드:**

#### 메타데이터 관련 메서드

##### `get_urns()`
필터를 적용하여 데이터셋의 URN 목록을 가져옵니다.

**반환값:**
- URN 목록

##### `get_table_name(urn)`
URN에 대한 테이블 이름을 가져옵니다.

**파라미터:**
- `urn` (str): 데이터셋 URN

**반환값:**
- `str`: 테이블 이름 (database.table 형태) 또는 None

##### `get_table_description(urn)`
URN에 대한 테이블 설명을 가져옵니다.

**파라미터:**
- `urn` (str): 데이터셋 URN

**반환값:**
- `str`: 테이블 설명 또는 None

##### `get_column_names_and_descriptions(urn)`
URN에 대한 컬럼 이름 및 설명을 가져옵니다.

**파라미터:**
- `urn` (str): 데이터셋 URN

**반환값:**
- `list`: 컬럼 정보 리스트 (각 항목: column_name, column_description, column_type)

##### `get_table_lineage(urn, counts=100, direction="DOWNSTREAM", degree_values=None)`
URN에 대한 DOWNSTREAM/UPSTREAM lineage entity를 가져옵니다.

**파라미터:**
- `urn` (str): 데이터셋 URN
- `counts` (int): 가져올 엔티티 수 (기본값: 100)
- `direction` (str): 리니지 방향 ("DOWNSTREAM" 또는 "UPSTREAM", 기본값: "DOWNSTREAM")
- `degree_values` (list): 필터링할 degree 값 리스트 (기본값: ["1", "2"])

**반환값:**
- `tuple`: (urn, lineage_result)

##### `get_column_lineage(urn)`
URN에 대한 UPSTREAM lineage의 column source를 가져옵니다.

**파라미터:**
- `urn` (str): 데이터셋 URN

**반환값:**
- `dict`: 컬럼 리니지 정보
  - `downstream_dataset`: 다운스트림 데이터셋 이름
  - `lineage_by_upstream_dataset`: 업스트림 데이터셋별 컬럼 매핑

##### `min_degree_lineage(lineage_result)`
lineage 중 최소 degree만 가져옵니다.

**파라미터:**
- `lineage_result`: `get_table_lineage`의 반환값

**반환값:**
- `dict`: 테이블별 최소 degree 매핑

##### `build_table_metadata(urn, max_degree=2, sort_by_degree=True)`
테이블 단위로 통합 메타데이터를 생성합니다.

**파라미터:**
- `urn` (str): 데이터셋 URN
- `max_degree` (int): 최대 degree 제한 (기본값: 2)
- `sort_by_degree` (bool): degree 기준 정렬 여부 (기본값: True)

**반환값:**
- `dict`: 통합 메타데이터
  - `table_name`: 테이블 이름
  - `description`: 테이블 설명
  - `columns`: 컬럼 정보 리스트
  - `lineage`: 리니지 정보

##### `get_urn_info(urn)`
특정 URN에 대한 모든 관련 정보를 가져옵니다.

**파라미터:**
- `urn` (str): 조회할 데이터셋 URN

**반환값:**
- `dict`: URN에 대한 전체 메타데이터 정보

##### `_print_urn_details(metadata)`
URN 메타데이터를 보기 좋게 출력하는 내부 함수입니다.

#### 용어집 관련 메서드

##### `get_root_glossary_nodes()`
DataHub에서 루트 용어집 노드를 가져옵니다.

**반환값:**
- `dict`: 루트 용어집 노드 정보

##### `get_glossary_node_by_urn(urn)`
특정 URN의 용어집 노드 및 그 자식 항목을 가져옵니다.

**파라미터:**
- `urn` (str): 용어집 노드의 URN

**반환값:**
- `dict`: 용어집 노드 정보와 자식 항목

##### `get_node_basic_info(node, index)`
용어집 노드의 기본 정보를 딕셔너리로 반환합니다.

**파라미터:**
- `node` (dict): 용어집 노드 정보
- `index` (int): 노드의 인덱스

**반환값:**
- `dict`: 노드의 기본 정보

##### `get_child_entity_info(entity, index)`
자식 엔티티(용어 또는 노드)의 정보를 딕셔너리로 반환합니다.

**파라미터:**
- `entity` (dict): 자식 엔티티 정보
- `index` (int): 엔티티의 인덱스

**반환값:**
- `dict`: 엔티티 정보

##### `process_node_details(node)`
노드의 상세 정보를 처리하고 딕셔너리로 반환합니다.

**파라미터:**
- `node` (dict): 용어집 노드 정보

**반환값:**
- `dict`: 노드의 상세 정보

##### `process_glossary_nodes(result)`
용어집 노드 결과를 처리하고 딕셔너리로 반환합니다.

**파라미터:**
- `result` (dict): API 응답 결과

**반환값:**
- `dict`: 처리된 용어집 노드 데이터

##### `get_glossary_data()`
DataHub에서 전체 용어집 데이터를 가져와 처리합니다.

**반환값:**
- `dict`: 처리된 용어집 데이터

##### `get_glossary_terms_by_urn(dataset_urn)`
특정 데이터셋 URN의 glossary terms를 조회합니다.

**파라미터:**
- `dataset_urn` (str): 데이터셋 URN

**반환값:**
- `dict`: glossary terms 정보

#### 쿼리 관련 메서드

##### `get_queries(start=0, count=10, query="*", filters=None)`
DataHub에서 쿼리 목록을 가져옵니다.

**파라미터:**
- `start` (int): 시작 인덱스 (기본값: 0)
- `count` (int): 반환할 쿼리 수 (기본값: 10)
- `query` (str): 필터링에 사용할 쿼리 문자열 (기본값: "*")
- `filters` (list): 추가 필터 (기본값: None)

**반환값:**
- `dict`: 쿼리 목록 정보

##### `process_queries(result)`
쿼리 목록 결과를 처리하고 간소화된 형태로 반환합니다.

**파라미터:**
- `result` (dict): API 응답 결과

**반환값:**
- `dict`: 처리된 쿼리 목록 데이터

##### `get_query_data(start=0, count=10, query="*", filters=None)`
DataHub에서 쿼리 목록을 가져와 처리합니다.

**파라미터:**
- `start` (int): 시작 인덱스 (기본값: 0)
- `count` (int): 반환할 쿼리 수 (기본값: 10)
- `query` (str): 필터링에 사용할 쿼리 문자열 (기본값: "*")
- `filters` (list): 추가 필터 (기본값: None)

**반환값:**
- `dict`: 처리된 쿼리 목록 데이터

##### `get_queries_by_urn(dataset_urn)`
특정 데이터셋 URN과 연관된 쿼리들을 조회합니다.

**파라미터:**
- `dataset_urn` (str): 데이터셋 URN

**반환값:**
- `dict`: 연관된 쿼리 목록

**의존성:**
- `utils.data.datahub_services.base_client.DataHubBaseClient`: 기본 클라이언트
- `utils.data.datahub_services.metadata_service.MetadataService`: 메타데이터 서비스
- `utils.data.datahub_services.query_service.QueryService`: 쿼리 서비스
- `utils.data.datahub_services.glossary_service.GlossaryService`: 용어집 서비스

**사용 예시:**
```python
from utils.data.datahub_source import DatahubMetadataFetcher

# 페처 초기화
fetcher = DatahubMetadataFetcher(gms_server="http://localhost:8080")

# 테이블 메타데이터 조회
urn = "urn:li:dataset:(urn:li:dataPlatform:postgres,db.schema.table,TABLE)"
metadata = fetcher.get_urn_info(urn)

# 용어집 조회
glossary_data = fetcher.get_glossary_data()

# 쿼리 조회
queries = fetcher.get_query_data(start=0, count=10)
```

**import 되어 사용되는 위치:**
- `utils/llm/tools/datahub.py`: `from utils.data.datahub_source import DatahubMetadataFetcher`

---

### `queries.py`

DataHub GraphQL 쿼리 모음 파일입니다. DataHub GMS 서버와 통신하기 위한 모든 GraphQL 쿼리 문자열을 포함합니다.

**주요 쿼리:**

#### `ROOT_GLOSSARY_NODES_QUERY`
루트 용어집 노드를 조회하는 쿼리입니다. 4단계 계층 구조까지 포함합니다.

**사용 위치:**
- `utils.data.datahub_services.glossary_service.GlossaryService.get_root_glossary_nodes()`

#### `GLOSSARY_NODE_QUERY`
특정 URN의 용어집 노드 상세 정보를 조회하는 쿼리입니다. 자식 노드, 용어, 소유권, 권한 등의 상세 정보를 포함합니다.

**파라미터:**
- `urn` (str): 용어집 노드 URN

**사용 위치:**
- `utils.data.datahub_services.glossary_service.GlossaryService.get_glossary_node_by_urn()`

#### `LIST_QUERIES_QUERY`
쿼리 목록을 조회하는 쿼리입니다. URN, 이름, 설명, SQL 문, 데이터셋 정보 등을 포함합니다.

**파라미터:**
- `input` (dict): ListQueriesInput
  - `start` (int): 시작 인덱스
  - `count` (int): 반환할 항목 수
  - `query` (str): 검색 쿼리
  - `filters` (list, optional): 추가 필터

**사용 위치:**
- `utils.data.datahub_services.query_service.QueryService.get_queries()`

#### `QUERIES_BY_URN_QUERY`
특정 URN과 연관된 쿼리를 조회하는 단순화된 쿼리입니다.

**파라미터:**
- `input` (dict): ListQueriesInput

**사용 위치:**
- `utils.data.datahub_services.query_service.QueryService.get_queries_by_urn()`

#### `GLOSSARY_TERMS_BY_URN_QUERY`
특정 데이터셋 URN의 glossary terms를 조회하는 쿼리입니다.

**파라미터:**
- `urn` (str): 데이터셋 URN

**사용 위치:**
- `utils.data.datahub_services.glossary_service.GlossaryService.get_glossary_terms_by_urn()`
- `utils.data.datahub_services.query_service.QueryService.get_glossary_terms_by_urn()`

**import 되어 사용되는 위치:**
- `utils.data.datahub_services.glossary_service`: `from utils.data.queries import ...`
- `utils.data.datahub_services.query_service`: `from utils.data.queries import ...`

---

### `datahub_services/`

DataHub와의 상호작용을 위한 서비스 모듈들을 제공하는 서브패키지입니다.

**주요 구성요소:**
- `base_client.py`: 기본 연결 및 통신
- `glossary_service.py`: 용어집 서비스
- `metadata_service.py`: 메타데이터 서비스
- `query_service.py`: 쿼리 서비스
- `__init__.py`: 패키지 초기화 및 exports

상세한 문서는 [datahub_services/README.md](datahub_services/README.md)를 참조하세요.

---

## 전체 사용 예시

### 예시 1: 기본 사용법

```python
from utils.data.datahub_source import DatahubMetadataFetcher

# 페처 초기화
fetcher = DatahubMetadataFetcher(gms_server="http://localhost:8080")

# 테이블 메타데이터 조회
urn = "urn:li:dataset:(urn:li:dataPlatform:postgres,db.schema.table,TABLE)"
metadata = fetcher.get_urn_info(urn)

# 용어집 조회
glossary_data = fetcher.get_glossary_data()

# 쿼리 조회
queries = fetcher.get_query_data(start=0, count=10)
```

### 예시 2: 분리된 서비스 사용

```python
from utils.data.datahub_services import (
    DataHubBaseClient,
    MetadataService,
    QueryService,
    GlossaryService
)

# 클라이언트 초기화
client = DataHubBaseClient(gms_server="http://localhost:8080")

# 서비스 초기화
metadata_service = MetadataService(client)
query_service = QueryService(client)
glossary_service = GlossaryService(client)

# 메타데이터 조회
urn = "urn:li:dataset:(...)"
metadata = metadata_service.build_table_metadata(urn)

# 쿼리 조회
queries = query_service.get_query_data(start=0, count=10)

# 용어집 조회
glossary_data = glossary_service.get_glossary_data()
```

### 예시 3: 개별 메서드 사용

```python
from utils.data.datahub_source import DatahubMetadataFetcher

fetcher = DatahubMetadataFetcher(gms_server="http://localhost:8080")

# 테이블 정보 조회
urn = "urn:li:dataset:(...)"
table_name = fetcher.get_table_name(urn)
description = fetcher.get_table_description(urn)
columns = fetcher.get_column_names_and_descriptions(urn)

# 리니지 조회
downstream_lineage = fetcher.get_table_lineage(urn, direction="DOWNSTREAM")
upstream_lineage = fetcher.get_table_lineage(urn, direction="UPSTREAM")
column_lineage = fetcher.get_column_lineage(urn)

# 최소 degree 필터링
min_degree = fetcher.min_degree_lineage(downstream_lineage)
```

---

## 의존성

### 외부 패키지
- `requests`: HTTP 요청 처리
- `datahub`: DataHub Python SDK
  - `datahub.emitter.rest_emitter.DatahubRestEmitter`
  - `datahub.ingestion.graph.client.DatahubClientConfig`
  - `datahub.ingestion.graph.client.DataHubGraph`
  - `datahub.metadata.schema_classes`

### 내부 패키지
- `utils.data.queries`: GraphQL 쿼리 정의 모듈
- `utils.data.datahub_services.*`: DataHub 서비스 레이어

---

## 참고 사항

1. `DatahubMetadataFetcher`는 하위 호환성을 위해 분리된 서비스들을 내부적으로 사용합니다.
2. 모든 서비스는 `DataHubBaseClient`를 필요로 합니다.
3. GMS 서버 URL은 초기화 시 유효성 검사가 수행됩니다.
4. GraphQL 쿼리는 `queries.py`에 중앙 집중식으로 정의되어 있습니다.
5. 오류 발생 시 dict 형태로 `{"error": True, "message": "..."}` 구조로 반환됩니다.
6. `utils/llm/tools/datahub.py`에서 `DatahubMetadataFetcher`를 import하여 LLM 도구로 사용됩니다.

