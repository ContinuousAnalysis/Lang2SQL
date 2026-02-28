from __future__ import annotations

from ...core.catalog import CatalogEntry, TextDocument
from ...core.exceptions import IntegrationMissingError
from ...core.ports import CatalogLoaderPort

try:
    import datahub as _datahub  # type: ignore[import]
except ImportError:
    _datahub = None  # type: ignore[assignment]


class DataHubCatalogLoader(CatalogLoaderPort):
    """DataHub URN → list[CatalogEntry] 변환.

    DataHub GMS 서버에서 테이블 메타데이터를 조회하여
    v2 아키텍처의 CatalogEntry 포맷으로 변환한다.
    """

    def __init__(
        self,
        gms_server: str = "http://localhost:8080",
        extra_headers: dict | None = None,
    ) -> None:
        if _datahub is None:
            raise IntegrationMissingError(
                "acryl-datahub",
                hint="pip install acryl-datahub",
            )
        # 레거시 DatahubMetadataFetcher를 내부에서 wrapping
        from utils.data.datahub_source import DatahubMetadataFetcher  # type: ignore[import]

        self._fetcher = DatahubMetadataFetcher(
            gms_server=gms_server,
            extra_headers=extra_headers or {},
        )

    def load(self, urns: list[str] | None = None) -> list[CatalogEntry]:
        """DataHub에서 CatalogEntry 목록을 로드한다.

        Args:
            urns: 조회할 URN 목록. None이면 전체 URN을 조회한다.

        Returns:
            CatalogEntry 목록
        """
        if urns is None:
            urns = list(self._fetcher.get_urns())

        entries: list[CatalogEntry] = []
        for urn in urns:
            name = self._fetcher.get_table_name(urn) or ""
            description = self._fetcher.get_table_description(urn) or ""
            raw_cols = self._fetcher.get_column_names_and_descriptions(urn) or []
            columns: dict[str, str] = {
                col["column_name"]: col.get("column_description") or ""
                for col in raw_cols
            }
            entries.append(
                CatalogEntry(name=name, description=description, columns=columns)
            )
        return entries

    def load_lineage_documents(
        self,
        urns: list[str] | None = None,
        max_degree: int = 2,
    ) -> list[TextDocument]:
        """DataHub lineage 정보를 TextDocument 목록으로 변환한다.

        내부적으로 build_table_metadata()를 사용하며, 사이클 안전성은
        하위 레이어에서 보장된다:
          - get_table_lineage(): GraphQL degree 필터로 depth 상한 적용
          - min_degree_lineage(): 테이블별 최소 degree만 유지 (사이클 경로 dedup)
          - build_table_metadata(): 자기 자신(table == current_table) 제외

        Args:
            urns:       조회할 URN 목록. None이면 전체 URN을 조회한다.
            max_degree: 포함할 최대 lineage depth. 기본값 2.

        Returns:
            TextDocument 목록. lineage 없는 테이블은 제외된다.

        Usage::

            loader = DataHubCatalogLoader(gms_server="http://localhost:8080")
            pipeline = EnrichedNL2SQL(
                catalog=loader.load(),
                documents=loader.load_lineage_documents(),
                llm=..., db=..., embedding=...,
            )
        """
        if urns is None:
            urns = list(self._fetcher.get_urns())

        return [
            doc
            for urn in urns
            if (doc := self._urn_to_lineage_document(urn, max_degree)) is not None
        ]

    def _urn_to_lineage_document(
        self, urn: str, max_degree: int
    ) -> TextDocument | None:
        """단일 URN의 lineage를 TextDocument로 변환. lineage 없으면 None 반환."""
        try:
            # build_table_metadata가 upstream/downstream/column lineage를
            # 파싱 및 dedup까지 처리해준다.
            meta = self._fetcher.build_table_metadata(urn, max_degree=max_degree)
        except Exception:
            return None

        table_name = meta.get("table_name") or ""
        lineage = meta.get("lineage", {})
        upstream = lineage.get("upstream", [])
        downstream = lineage.get("downstream", [])
        upstream_columns = lineage.get("upstream_columns", [])

        if not upstream and not downstream and not upstream_columns:
            return None

        return TextDocument(
            id=f"lineage__{table_name}",
            title=f"{table_name} 리니지",
            content=self._format_lineage(
                table_name, upstream, downstream, upstream_columns
            ),
            source="datahub",
            metadata={"urn": urn, "table_name": table_name},
        )

    @staticmethod
    def _format_lineage(
        table_name: str,
        upstream: list[dict],
        downstream: list[dict],
        upstream_columns: list[dict],
    ) -> str:
        """lineage 데이터를 자연어 텍스트로 포맷한다."""
        lines: list[str] = [f"테이블: {table_name}", ""]

        if upstream:
            lines += ["[Upstream — 이 테이블의 원천 데이터]"]
            lines += [f"  - {t['table']} (depth: {t['degree']})" for t in upstream]
            lines.append("")

        if downstream:
            lines += ["[Downstream — 이 테이블을 참조하는 테이블]"]
            lines += [f"  - {t['table']} (depth: {t['degree']})" for t in downstream]
            lines.append("")

        if upstream_columns:
            lines += ["[컬럼 단위 Upstream Lineage]"]
            for dataset in upstream_columns:
                lines.append(f"  {dataset.get('upstream_dataset', '')}:")
                lines += [
                    f"    {col['upstream_column']} → {col['downstream_column']}"
                    f" (신뢰도: {col.get('confidence', 1.0):.2f})"
                    for col in dataset.get("columns", [])
                ]
            lines.append("")

        return "\n".join(lines).strip()
