from __future__ import annotations

from ...core.catalog import CatalogEntry
from ...core.exceptions import IntegrationMissingError

try:
    import datahub as _datahub  # type: ignore[import]
except ImportError:
    _datahub = None  # type: ignore[assignment]


class DataHubCatalogLoader:
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
