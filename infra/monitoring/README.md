# infra/monitoring 패키지

서버 상태 확인 및 헬스 체크 기능을 제공하는 모니터링 패키지입니다.

## 디렉토리 구조

```
infra/monitoring/
├── __init__.py
├── __pycache__/
└── check_server.py
```

## 파일 설명

### `__init__.py`

모니터링/헬스체크 패키지의 초기화 파일입니다.

**내용:**
- 패키지 문서화 문자열: "모니터링/헬스체크 패키지"

**역할:**
- `infra.monitoring` 패키지를 Python 패키지로 인식시키는 초기화 파일

---

### `check_server.py`

서버 상태 확인 및 연결 관련 기능을 제공하는 유틸리티 클래스입니다.

**주요 구성 요소:**

1. **HTTP 기반 서버 헬스 체크**
   - `/health` 엔드포인트를 통한 서버 상태 확인
   - 향후 서버 연결 또는 상태 점검 기능 확장 가능한 구조

2. **예외 처리 및 로깅**
   - 요청 실패, 타임아웃, 연결 오류 등의 다양한 예외 상황 처리
   - 로깅을 통해 상세한 실패 원인 기록
   - 결과를 boolean 값으로 반환

**주요 클래스:**

#### `CheckServer`

서버의 상태를 확인하거나 연결을 테스트하는 유틸리티 메서드를 제공하는 클래스입니다.

현재는 GMS 서버의 `/health` 엔드포인트에 대한 헬스 체크 기능을 포함하고 있으며, 향후에는 다양한 서버 연결 확인 및 상태 점검 기능이 추가될 수 있도록 확장 가능한 구조로 설계되었습니다.

**메서드:**

- `is_gms_server_healthy(*, url: str) -> bool` (정적 메서드):
  - 지정된 GMS 서버의 `/health` 엔드포인트에 요청을 보내 상태를 확인합니다.
  - Parameters:
    - `url` (str): 헬스 체크를 수행할 GMS 서버의 기본 URL (예: "http://localhost:8080")
  - Returns:
    - `bool`: 서버가 정상적으로 응답하면 `True`, 예외 발생 시 `False`
  - 기능:
    - 서버 URL과 `/health` 경로를 결합하여 헬스 체크 엔드포인트 생성
    - 3초 타임아웃으로 GET 요청 수행
    - HTTP 200 응답 시 `True` 반환
    - 다음 예외 상황 처리:
      - `ConnectTimeout`, `ReadTimeout`: 타임아웃 오류 로깅
      - `ConnectionError`: 연결 실패 로깅
      - `HTTPError`: HTTP 오류 로깅
      - `RequestException`: 기타 요청 예외 로깅
    - 예외 발생 시 `False` 반환

**의존성:**
- `requests`: HTTP 요청 수행
- `urllib.parse.urljoin`: URL 경로 결합
- `logging`: 로깅 기능

**사용 예시:**

```python
from infra.monitoring.check_server import CheckServer

# GMS 서버 헬스 체크
is_healthy = CheckServer.is_gms_server_healthy(url="http://localhost:8080")

if is_healthy:
    print("서버가 정상입니다.")
else:
    print("서버 연결에 문제가 있습니다.")
```

## Import 및 사용 현황

### 사용 위치

**`interface/app_pages/settings_sections/data_source_section.py`**

이 모듈에서 `CheckServer` 클래스를 import하여 사용합니다.

**Import:**
```python
from infra.monitoring.check_server import CheckServer
```

**사용 방법:**

1. **DataHub 편집 시 헬스 체크** (117번째 줄)
   ```python
   if st.button("헬스 체크", key="dh_edit_health"):
       ok = CheckServer.is_gms_server_healthy(url=new_url)
       st.session_state["datahub_last_health"] = bool(ok)
       if ok:
           st.success("GMS 서버가 정상입니다.")
       else:
           st.error("GMS 서버 헬스 체크 실패. URL과 네트워크를 확인하세요.")
   ```

2. **DataHub 추가 시 헬스 체크** (160번째 줄)
   ```python
   if st.button("헬스 체크", key="dh_health_new"):
       ok = CheckServer.is_gms_server_healthy(url=dh_url)
       st.session_state["datahub_last_health"] = bool(ok)
       if ok:
           st.success("GMS 서버가 정상입니다.")
       else:
           st.error("GMS 서버 헬스 체크 실패. URL과 네트워크를 확인하세요.")
   ```

**사용 목적:**
- Streamlit UI에서 DataHub 서버 설정 시, 사용자가 입력한 URL이 유효한지 확인
- 헬스 체크 결과를 세션 상태에 저장하여 상태 배너에 표시
- 서버 연결 성공/실패에 따라 사용자에게 적절한 피드백 제공

## 로깅

모듈은 Python의 `logging` 모듈을 사용하여 다음 정보를 로깅합니다:
- 서버가 정상일 때: INFO 레벨로 성공 메시지
- 타임아웃 발생 시: ERROR 레벨로 타임아웃 오류 메시지
- 연결 실패 시: ERROR 레벨로 연결 오류 메시지
- HTTP 오류 발생 시: ERROR 레벨로 HTTP 오류 메시지
- 기타 요청 예외 발생 시: ERROR 레벨로 예외 정보 로깅

로깅 레벨은 `INFO`로 설정되어 있으며, 타임스탬프와 로그 레벨 정보가 포함됩니다.

**로깅 포맷:**
```
%(asctime)s [%(levelname)s] %(message)s
```

날짜 형식: `%Y-%m-%d %H:%M:%S`

