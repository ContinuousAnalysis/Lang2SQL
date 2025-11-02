# DataHub Services 패키지

DataHub와의 상호작용을 위한 서비스 모듈들을 제공하는 패키지입니다.

## 디렉토리 구조

```
datahub_services/
├── __init__.py              # 패키지 초기화 및 exports
├── base_client.py           # 기본 클라이언트
├── glossary_service.py      # 용어집 서비스
├── metadata_service.py      # 메타데이터 서비스
└── query_service.py         # 쿼리 서비스
```

## 파일별 상세 내용

### `__init__.py`

패키지의 진입점이며, 주요 서비스 클래스들을 export합니다.

**Export되는 클래스:**
- `DataHubBaseClient`: 기본 연결 및 통신 클라이언트
- `MetadataService`: 메타데이터, 리니지, URN 관련 서비스
- `QueryService`: 쿼리 관련 서비스
- `GlossaryService`: 용어집 관련 서비스

**사용 방법:**
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
```

---

### `base_client.py`

DataHub GMS 서버와의 기본 연결 및 통신 기능을 제공하는 클라이언트입니다.

**클래스:**
- `DataHubBaseClient`

**주요 메서드:**

#### `__init__(self, gms_server="http://localhost:8080", extra_headers={})`
DataHub 클라이언트를 초기화합니다.

**파라미터:**
- `gms_server` (str): DataHub GMS 서버 URL
- `extra_headers` (dict): 추가 HTTP 헤더

**사용 예시:**
```python
from utils.data.datahub_services import DataHubBaseClient

client = DataHubBaseClient(gms_server="http://localhost:8080")
```

#### `_is_valid_gms_server(self, gms_server)`
GMS 서버 주소의 유효성을 검사합니다.

**파라미터:**
- `gms_server` (str): 검사할 GMS 서버 URL

**반환값:**
- `bool`: 서버가 유효한 경우 True

#### `execute_graphql_query(self, query, variables=None)`
GraphQL 쿼리를 실행합니다.

**파라미터:**
- `query` (str): GraphQL 쿼리 문자열
- `variables` (dict, optional): 쿼리 변수

**반환값:**
- `dict`: GraphQL 응답 또는 오류 정보

**사용 예시:**
```python
query = "{ health { status } }"
result = client.execute_graphql_query(query)
```

#### `get_datahub_graph(self)`
DataHub Graph 클라이언트를 반환합니다.

**반환값:**
- DataHub Graph 객체

#### `get_urns(self)`
필터를 적용하여 데이터셋의 URN 목록을 가져옵니다.

**반환값:**
- URN 목록

**의존성:**
- `requests`: HTTP 요청 처리
- `datahub.emitter.rest_emitter.DatahubRestEmitter`: DataHub REST emitter

---

### `glossary_service.py`

DataHub의 용어집(Glossary) 관련 기능을 제공하는 서비스입니다.

**클래스:**
- `GlossaryService`

**초기화:**
```python
from utils.data.datahub_services import DataHubBaseClient, GlossaryService

client = DataHubBaseClient(gms_server="http://localhost:8080")
glossary_service = GlossaryService(client)
```

**주요 메서드:**

#### `get_root_glossary_nodes(self)`
DataHub에서 루트 용어집 노드를 가져옵니다.

**반환값:**
- `dict`: 루트 용어집 노드 정보

#### `get_glossary_node_by_urn(self, urn)`
특정 URN의 용어집 노드 및 그 자식 항목을 가져옵니다.

**파라미터:**
- `urn` (str): 용어집 노드의 URN

**반환값:**
- `dict`: 용어집 노드 정보와 자식 항목

#### `get_node_basic_info(self, node, index)`
용어집 노드의 기본 정보를 딕셔너리로 반환합니다.

**파라미터:**
- `node` (dict): 용어집 노드 정보
- `index` (int): 노드의 인덱스

**반환값:**
- `dict`: 노드의 기본 정보 (index, name, description, child_count 등)

#### `get_child_entity_info(self, entity, index)`
자식 엔티티(용어 또는 노드)의 정보를 딕셔너리로 반환합니다.

**파라미터:**
- `entity` (dict): 자식 엔티티 정보
- `index` (int): 엔티티의 인덱스

**반환값:**
- `dict`: 엔티티 정보 (index, type, name, description 등)

#### `process_node_details(self, node)`
노드의 상세 정보를 처리하고 딕셔너리로 반환합니다.

**파라미터:**
- `node` (dict): 용어집 노드 정보

**반환값:**
- `dict`: 노드의 상세 정보 (name, children 등)

#### `process_glossary_nodes(self, result)`
용어집 노드 결과를 처리하고 딕셔너리로 반환합니다.

**파라미터:**
- `result` (dict): API 응답 결과

**반환값:**
- `dict`: 처리된 용어집 노드 데이터 (total_nodes, nodes)

#### `get_glossary_data(self)`
DataHub에서 전체 용어집 데이터를 가져와 처리합니다.

**반환값:**
- `dict`: 처리된 용어집 데이터 또는 오류 정보

**사용 예시:**
```python
result = glossary_service.get_glossary_data()
print(f"전체 노드 수: {result['total_nodes']}")
for node in result['nodes']:
    print(f"  - {node['name']}: {node.get('description', 'N/A')}")
```

#### `get_glossary_terms_by_urn(self, dataset_urn)`
특정 데이터셋 URN의 glossary terms를 조회합니다.

**파라미터:**
- `dataset_urn` (str): 데이터셋 URN

**반환값:**
- `dict`: glossary terms 정보

**의존성:**
- `utils.data.datahub_services.base_client.DataHubBaseClient`: 기본 클라이언트
- `utils.data.queries`: GraphQL 쿼리 정의
  - `GLOSSARY_NODE_QUERY`
  - `GLOSSARY_TERMS_BY_URN_QUERY`
  - `ROOT_GLOSSARY_NODES_QUERY`

---

### `metadata_service.py`

테이블 메타데이터, 리니지, URN 관련 기능을 제공하는 서비스입니다.

**클래스:**
- `MetadataService`

**초기화:**
```python
from utils.data.datahub_services import DataHubBaseClient, MetadataService

client = DataHubBaseClient(gms_server="http://localhost:8080")
metadata_service = MetadataService(client)
```

**주요 메서드:**

#### `get_table_name(self, urn)`
URN에 대한 테이블 이름을 가져옵니다.

**파라미터:**
- `urn` (str): 데이터셋 URN

**반환값:**
- `str`: 테이블 이름 (database.table 형태) 또는 None

#### `get_table_description(self, urn)`
URN에 대한 테이블 설명을 가져옵니다.

**파라미터:**
- `urn` (str): 데이터셋 URN

**반환값:**
- `str`: 테이블 설명 또는 None

#### `get_column_names_and_descriptions(self, urn)`
URN에 대한 컬럼 이름 및 설명을 가져옵니다.

**파라미터:**
- `urn` (str): 데이터셋 URN

**반환값:**
- `list`: 컬럼 정보 리스트 (각 항목: column_name, column_description, column_type)

#### `get_table_lineage(self, urn, counts=100, direction="DOWNSTREAM", degree_values=None)`
URN에 대한 DOWNSTREAM/UPSTREAM lineage entity를 가져옵니다.

**파라미터:**
- `urn` (str): 데이터셋 URN
- `counts` (int): 가져올 엔티티 수 (기본값: 100)
- `direction` (str): 리니지 방향 ("DOWNSTREAM" 또는 "UPSTREAM", 기본값: "DOWNSTREAM")
- `degree_values` (list): 필터링할 degree 값 리스트 (기본값: ["1", "2"])

**반환값:**
- `tuple`: (urn, lineage_result)

#### `get_column_lineage(self, urn)`
URN에 대한 UPSTREAM lineage의 column source를 가져옵니다.

**파라미터:**
- `urn` (str): 데이터셋 URN

**반환값:**
- `dict`: 컬럼 리니지 정보
  - `downstream_dataset`: 다운스트림 데이터셋 이름
  - `lineage_by_upstream_dataset`: 업스트림 데이터셋별 컬럼 매핑
    - `upstream_dataset`: 업스트림 데이터셋 이름
    - `columns`: 컬럼 매핑 리스트
      - `upstream_column`: 업스트림 컬럼
      - `downstream_column`: 다운스트림 컬럼
      - `confidence`: 신뢰도

#### `min_degree_lineage(self, lineage_result)`
lineage 중 최소 degree만 가져옵니다.

**파라미터:**
- `lineage_result`: `get_table_lineage`의 반환값

**반환값:**
- `dict`: 테이블별 최소 degree 매핑

#### `build_table_metadata(self, urn, max_degree=2, sort_by_degree=True)`
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
    - `downstream`: 다운스트림 테이블 리스트
    - `upstream`: 업스트림 테이블 리스트
    - `upstream_columns`: 컬럼 레벨 리니지

**사용 예시:**
```python
metadata = metadata_service.build_table_metadata(urn)
print(f"테이블: {metadata['table_name']}")
print(f"컬럼 수: {len(metadata['columns'])}")
print(f"다운스트림: {len(metadata['lineage']['downstream'])}개")
print(f"업스트림: {len(metadata['lineage']['upstream'])}개")
```

#### `get_urn_info(self, urn)`
특정 URN에 대한 모든 관련 정보를 가져옵니다.

**파라미터:**
- `urn` (str): 조회할 데이터셋 URN

**반환값:**
- `dict`: URN에 대한 전체 메타데이터 정보 또는 오류 정보

**사용 예시:**
```python
result = metadata_service.get_urn_info(urn)
# 콘솔에 자동으로 포맷된 정보 출력 및 반환
```

**의존성:**
- `collections.defaultdict`: 딕셔너리 기본값 처리
- `datahub.ingestion.graph.client`: DataHub Graph 클라이언트
  - `DatahubClientConfig`
  - `DataHubGraph`
- `datahub.metadata.schema_classes`: DataHub 메타데이터 스키마 클래스
  - `DatasetPropertiesClass`
  - `SchemaMetadataClass`
  - `UpstreamLineageClass`
- `utils.data.datahub_services.base_client.DataHubBaseClient`: 기본 클라이언트

---

### `query_service.py`

DataHub의 쿼리 관련 기능을 제공하는 서비스입니다.

**클래스:**
- `QueryService`

**초기화:**
```python
from utils.data.datahub_services import DataHubBaseClient, QueryService

client = DataHubBaseClient(gms_server="http://localhost:8080")
query_service = QueryService(client)
```

**주요 메서드:**

#### `get_queries(self, start=0, count=10, query="*", filters=None)`
DataHub에서 쿼리 목록을 가져옵니다.

**파라미터:**
- `start` (int): 시작 인덱스 (기본값: 0)
- `count` (int): 반환할 쿼리 수 (기본값: 10)
- `query` (str): 필터링에 사용할 쿼리 문자열 (기본값: "*")
- `filters` (list): 추가 필터 (기본값: None)

**반환값:**
- `dict`: 쿼리 목록 정보

#### `process_queries(self, result)`
쿼리 목록 결과를 처리하고 간소화된 형태로 반환합니다.

**파라미터:**
- `result` (dict): API 응답 결과

**반환값:**
- `dict`: 처리된 쿼리 목록 데이터
  - `total_queries`: 전체 쿼리 수
  - `count`: 조회된 쿼리 수
  - `start`: 시작 인덱스
  - `queries`: 쿼리 리스트 (urn, name, description, statement 포함)

#### `get_query_data(self, start=0, count=10, query="*", filters=None)`
DataHub에서 쿼리 목록을 가져와 처리합니다.

**파라미터:**
- `start` (int): 시작 인덱스 (기본값: 0)
- `count` (int): 반환할 쿼리 수 (기본값: 10)
- `query` (str): 필터링에 사용할 쿼리 문자열 (기본값: "*")
- `filters` (list): 추가 필터 (기본값: None)

**반환값:**
- `dict`: 처리된 쿼리 목록 데이터 또는 오류 정보

**사용 예시:**
```python
result = query_service.get_query_data(start=0, count=5, query="*")
print(f"전체 쿼리 수: {result['total_queries']}")
for idx, q in enumerate(result['queries'], 1):
    print(f"{idx}. {q['name']}: {q.get('description', 'N/A')}")
```

#### `get_queries_by_urn(self, dataset_urn)`
특정 데이터셋 URN과 연관된 쿼리들을 조회합니다.

**파라미터:**
- `dataset_urn` (str): 데이터셋 URN

**반환값:**
- `dict`: 연관된 쿼리 목록

**주의:** 전체 쿼리를 가져온 후 클라이언트 사이드에서 필터링하는 방식 사용

#### `get_glossary_terms_by_urn(self, dataset_urn)`
특정 데이터셋 URN의 glossary terms를 조회합니다.

**파라미터:**
- `dataset_urn` (str): 데이터셋 URN

**반환값:**
- `dict`: glossary terms 정보

**의존성:**
- `utils.data.datahub_services.base_client.DataHubBaseClient`: 기본 클라이언트
- `utils.data.queries`: GraphQL 쿼리 정의
  - `GLOSSARY_TERMS_BY_URN_QUERY`
  - `LIST_QUERIES_QUERY`
  - `QUERIES_BY_URN_QUERY`

---

## 전체 사용 예시

### 예시 1: 기본 사용법

```python
from utils.data.datahub_services import (
    DataHubBaseClient,
    MetadataService,
    QueryService,
    GlossaryService
)

# 1. 클라이언트 초기화
gms_server = "http://localhost:8080"
client = DataHubBaseClient(gms_server=gms_server)

# 2. 서비스 초기화
metadata_service = MetadataService(client)
query_service = QueryService(client)
glossary_service = GlossaryService(client)

# 3. 메타데이터 조회
urn = "urn:li:dataset:(...)"
metadata = metadata_service.get_urn_info(urn)

# 4. 쿼리 조회
queries = query_service.get_query_data(start=0, count=10)

# 5. 용어집 조회
glossary_data = glossary_service.get_glossary_data()
```

### 예시 2: 통합 페처 사용 (하위 호환성)

```python
from utils.data.datahub_source import DatahubMetadataFetcher

# 기존 인터페이스와 동일하게 사용 가능
fetcher = DatahubMetadataFetcher(gms_server="http://localhost:8080")

# 모든 메서드가 동일하게 동작
metadata = fetcher.get_urn_info(urn)
queries = fetcher.get_query_data()
glossary = fetcher.get_glossary_data()
```

### 예시 3: 테스트 코드

`test.py` 파일에서 실제 사용 예시를 확인할 수 있습니다:

```python
from utils.data.datahub_services import DataHubBaseClient, QueryService

client = DataHubBaseClient(gms_server="http://35.222.65.99:8080")
query_service = QueryService(client)

result = query_service.get_query_data(start=0, count=5, query="*")
print(json.dumps(result, indent=2, ensure_ascii=False))
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

---

## 참고 사항

1. 모든 서비스는 `DataHubBaseClient`를 필요로 합니다.
2. `DatahubMetadataFetcher`는 하위 호환성을 위해 이 서비스들을 내부적으로 사용합니다.
3. GMS 서버 URL은 초기화 시 유효성 검사가 수행됩니다.
4. GraphQL 쿼리는 `utils.data.queries` 모듈에 정의되어 있습니다.
5. 오류 발생 시 dict 형태로 `{"error": True, "message": "..."}` 구조로 반환됩니다.

