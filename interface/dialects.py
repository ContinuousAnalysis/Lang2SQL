"""
다이얼렉트 프리셋과 옵션 정의 모듈.

이 모듈은 다음을 제공합니다:

- DialectOption: 각 SQL 엔진 특성 데이터클래스
  - name: 엔진 표시 이름 (예: "PostgreSQL", "ClickHouse")
  - supports_ilike: 대소문자 무시 비교(ILIKE) 지원 여부
  - hints: 자주 쓰이는/효과적인 함수의 간결 목록 + 짧은 메모
    - 예: ["DATE_TRUNC (날짜 절단)", "STRING_AGG (문자 집계)"]

- PRESET_DIALECTS: 대표 SQL 엔진들의 기본 프리셋 모음
  - PostgreSQL, ClickHouse, Trino, Snowflake, Redshift, BigQuery, MSSQL, Oracle, DuckDB

주 사용처:
- Streamlit UI에서 프리셋 선택 및 커스텀 다이얼렉트 입력의 기준 데이터
- Lang2SQL 파이프라인에서 프롬프트/키워드 힌트 구성

주의:
- hints는 프롬프트 가이드용이며 실행 보장을 의미하지 않습니다.
- 실제 문법/함수 지원은 엔진 버전 및 설정에 따라 달라질 수 있습니다.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Dict, List


@dataclass
class DialectOption:
    name: str
    supports_ilike: bool = False
    hints: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict) -> "DialectOption":
        return DialectOption(
            name=data.get("name", "Custom"),
            supports_ilike=bool(data.get("supports_ilike", False)),
            hints=list(data.get("hints", data.get("keyword_hints", []))),
        )


PRESET_DIALECTS: Dict[str, DialectOption] = {
    "PostgreSQL": DialectOption(
        name="PostgreSQL",
        supports_ilike=True,
        hints=[
            "COALESCE (널 대체)",
            "DATE_TRUNC (날짜 절단)",
            "STRING_AGG (문자 집계)",
            "GENERATE_SERIES (시퀀스 생성)",
        ],
    ),
    "ClickHouse": DialectOption(
        name="ClickHouse",
        supports_ilike=False,
        hints=[
            "toDate (날짜 변환)",
            "dateDiff (날짜 차이)",
            "arrayJoin (배열 펼치기)",
            "groupArray (배열 집계)",
        ],
    ),
    "Trino": DialectOption(
        name="Trino",
        supports_ilike=False,
        hints=[
            "date_trunc (날짜 절단)",
            "try_cast (안전 변환)",
            "coalesce (널 대체)",
            "regexp_like (정규식 매칭)",
        ],
    ),
    "Snowflake": DialectOption(
        name="Snowflake",
        supports_ilike=True,
        hints=[
            "IFF (조건 분기)",
            "TO_DATE (날짜 변환)",
            "DATE_TRUNC (날짜 절단)",
            "LISTAGG (문자 집계)",
        ],
    ),
    "Redshift": DialectOption(
        name="Redshift",
        supports_ilike=True,
        hints=[
            "COALESCE (널 대체)",
            "DATE_TRUNC (날짜 절단)",
            "LISTAGG (문자 집계)",
            "REGEXP_REPLACE (정규식 치환)",
        ],
    ),
    "BigQuery": DialectOption(
        name="BigQuery",
        supports_ilike=False,
        hints=[
            "SAFE_CAST (안전 변환)",
            "DATE_TRUNC (날짜 절단)",
            "ARRAY_AGG (배열 집계)",
            "REGEXP_CONTAINS (정규식 포함)",
        ],
    ),
    "MSSQL": DialectOption(
        name="MSSQL",
        supports_ilike=False,
        hints=[
            "ISNULL (널 대체)",
            "DATEADD (날짜 가감)",
            "CONVERT (형 변환)",
            "STRING_AGG (문자 집계)",
        ],
    ),
    "Oracle": DialectOption(
        name="Oracle",
        supports_ilike=False,
        hints=[
            "NVL (널 대체)",
            "TO_DATE (날짜 변환)",
            "TRUNC (날짜 절단)",
            "LISTAGG (문자 집계)",
        ],
    ),
    "DuckDB": DialectOption(
        name="DuckDB",
        supports_ilike=True,
        hints=[
            "date_trunc (날짜 절단)",
            "string_agg (문자 집계)",
            "coalesce (널 대체)",
            "regexp_replace (정규식 치환)",
        ],
    ),
}
