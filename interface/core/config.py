from dataclasses import dataclass, field, asdict
from typing import List, Optional, Any, Dict
import os
from pathlib import Path
import json

try:
    import streamlit as st  # type: ignore
except Exception:  # pragma: no cover - streamlit may not be present in non-UI contexts
    st = None  # type: ignore

from llm_utils.tools import set_gms_server


DEFAULT_DATAHUB_SERVER = "http://localhost:8080"
DEFAULT_VECTORDB_TYPE = os.getenv("VECTORDB_TYPE", "faiss").lower()
DEFAULT_VECTORDB_LOCATION = os.getenv("VECTORDB_LOCATION", "")


@dataclass
class Config:
    datahub_server: str = DEFAULT_DATAHUB_SERVER
    vectordb_type: str = DEFAULT_VECTORDB_TYPE
    vectordb_location: str = DEFAULT_VECTORDB_LOCATION
    data_source_mode: str | None = None  # "datahub" | "vectordb" | None


@dataclass
class DataHubSource:
    name: str
    url: str
    faiss_path: Optional[str] = None
    note: Optional[str] = None


@dataclass
class VectorDBSource:
    name: str
    type: str  # 'faiss' | 'pgvector'
    location: str
    collection_prefix: Optional[str] = None
    note: Optional[str] = None


@dataclass
class DataSourcesRegistry:
    datahub: List[DataHubSource] = field(default_factory=list)
    vectordb: List[VectorDBSource] = field(default_factory=list)


def _get_session_value(key: str) -> str | None:
    if st is None:
        return None
    try:
        if key in st.session_state and st.session_state[key]:
            return str(st.session_state[key])
    except Exception:
        return None
    return None


def load_config() -> Config:
    """Load configuration with priority: session_state > environment > defaults."""
    datahub = _get_session_value("datahub_server") or os.getenv(
        "DATAHUB_SERVER", DEFAULT_DATAHUB_SERVER
    )
    mode = _get_session_value("data_source_mode")

    vectordb_type = _get_session_value("vectordb_type") or os.getenv(
        "VECTORDB_TYPE", DEFAULT_VECTORDB_TYPE
    )
    vectordb_location = _get_session_value("vectordb_location") or os.getenv(
        "VECTORDB_LOCATION", DEFAULT_VECTORDB_LOCATION
    )

    return Config(
        datahub_server=datahub,
        vectordb_type=vectordb_type.lower() if vectordb_type else DEFAULT_VECTORDB_TYPE,
        vectordb_location=vectordb_location,
        data_source_mode=mode,
    )


def update_datahub_server(config: Config, new_url: str) -> None:
    """Update DataHub server URL across runtime config, env-aware clients, and session."""
    if not new_url:
        return
    config.datahub_server = new_url

    # Propagate to underlying tooling/clients
    try:
        set_gms_server(new_url)
    except Exception:
        # Fail-soft: UI should surface errors from callers if needed
        pass

    # Reflect into session state for immediate UI reuse
    if st is not None:
        try:
            st.session_state["datahub_server"] = new_url
        except Exception:
            pass


# ---- Registry helpers ----


def get_data_sources_registry() -> DataSourcesRegistry:
    if st is not None and "data_sources_registry" in st.session_state:
        reg = st.session_state["data_sources_registry"]
        return reg  # stored as DataSourcesRegistry
    # Try load from disk
    try:
        registry = load_registry_from_disk()
    except Exception:
        registry = DataSourcesRegistry()
    if st is not None:
        st.session_state["data_sources_registry"] = registry
    return registry


def _save_registry(registry: DataSourcesRegistry) -> None:
    if st is not None:
        st.session_state["data_sources_registry"] = registry
    try:
        save_registry_to_disk(registry)
    except Exception:
        # fail-soft; UI will still have session copy
        pass


# ---- Disk persistence for registry ----


def _get_registry_file_path() -> Path:
    # Allow override via env var, else default to ./config/data_sources.json
    override = os.getenv("LANG2SQL_REGISTRY_PATH")
    if override:
        return Path(override).expanduser().resolve()
    return Path(os.getcwd()) / "config" / "data_sources.json"


def _ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def save_registry_to_disk(registry: DataSourcesRegistry) -> None:
    path = _get_registry_file_path()
    _ensure_parent_dir(path)
    payload = asdict(registry)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _parse_datahub_list(items: List[Dict[str, Any]]) -> List[DataHubSource]:
    parsed: List[DataHubSource] = []
    for item in items or []:
        name = str(item.get("name", "")).strip()
        url = str(item.get("url", "")).strip()
        faiss_path = item.get("faiss_path")
        note = item.get("note")
        if not name or not url:
            continue
        parsed.append(
            DataHubSource(name=name, url=url, faiss_path=faiss_path, note=note)
        )
    return parsed


def _parse_vectordb_list(items: List[Dict[str, Any]]) -> List[VectorDBSource]:
    parsed: List[VectorDBSource] = []
    for item in items or []:
        name = str(item.get("name", "")).strip()
        vtype = str(item.get("type", "")).strip().lower()
        location = str(item.get("location", "")).strip()
        if not name or not vtype or not location:
            continue
        collection_prefix = item.get("collection_prefix")
        note = item.get("note")
        parsed.append(
            VectorDBSource(
                name=name,
                type=vtype,
                location=location,
                collection_prefix=collection_prefix,
                note=note,
            )
        )
    return parsed


def load_registry_from_disk() -> DataSourcesRegistry:
    path = _get_registry_file_path()
    if not path.exists():
        return DataSourcesRegistry()
    with path.open("r", encoding="utf-8") as f:
        data: Dict[str, Any] = json.load(f)
    return DataSourcesRegistry(
        datahub=_parse_datahub_list(data.get("datahub", [])),
        vectordb=_parse_vectordb_list(data.get("vectordb", [])),
    )


def add_datahub_source(
    *, name: str, url: str, faiss_path: Optional[str] = None, note: Optional[str] = None
) -> None:
    registry = get_data_sources_registry()
    if any(s.name == name for s in registry.datahub):
        raise ValueError(f"이미 존재하는 DataHub 이름입니다: {name}")
    registry.datahub.append(
        DataHubSource(name=name, url=url, faiss_path=faiss_path, note=note)
    )
    _save_registry(registry)


def update_datahub_source(
    *, name: str, url: str, faiss_path: Optional[str], note: Optional[str]
) -> None:
    registry = get_data_sources_registry()
    for idx, s in enumerate(registry.datahub):
        if s.name == name:
            registry.datahub[idx] = DataHubSource(
                name=name, url=url, faiss_path=faiss_path, note=note
            )
            _save_registry(registry)
            return
    raise ValueError(f"존재하지 않는 DataHub 이름입니다: {name}")


def delete_datahub_source(*, name: str) -> None:
    registry = get_data_sources_registry()
    registry.datahub = [s for s in registry.datahub if s.name != name]
    _save_registry(registry)


def add_vectordb_source(
    *,
    name: str,
    vtype: str,
    location: str,
    collection_prefix: Optional[str] = None,
    note: Optional[str] = None,
) -> None:
    vtype = (vtype or "").lower()
    if vtype not in ("faiss", "pgvector"):
        raise ValueError("VectorDB 타입은 'faiss' 또는 'pgvector'여야 합니다")
    registry = get_data_sources_registry()
    if any(s.name == name for s in registry.vectordb):
        raise ValueError(f"이미 존재하는 VectorDB 이름입니다: {name}")
    registry.vectordb.append(
        VectorDBSource(
            name=name,
            type=vtype,
            location=location,
            collection_prefix=collection_prefix,
            note=note,
        )
    )
    _save_registry(registry)


def update_vectordb_source(
    *,
    name: str,
    vtype: str,
    location: str,
    collection_prefix: Optional[str],
    note: Optional[str],
) -> None:
    vtype = (vtype or "").lower()
    if vtype not in ("faiss", "pgvector"):
        raise ValueError("VectorDB 타입은 'faiss' 또는 'pgvector'여야 합니다")
    registry = get_data_sources_registry()
    for idx, s in enumerate(registry.vectordb):
        if s.name == name:
            registry.vectordb[idx] = VectorDBSource(
                name=name,
                type=vtype,
                location=location,
                collection_prefix=collection_prefix,
                note=note,
            )
            _save_registry(registry)
            return
    raise ValueError(f"존재하지 않는 VectorDB 이름입니다: {name}")


def delete_vectordb_source(*, name: str) -> None:
    registry = get_data_sources_registry()
    registry.vectordb = [s for s in registry.vectordb if s.name != name]
    _save_registry(registry)


def update_data_source_mode(config: Config, mode: str | None) -> None:
    """Persist user's data source selection (datahub | vectordb)."""
    config.data_source_mode = mode
    if st is not None:
        try:
            st.session_state["data_source_mode"] = mode
        except Exception:
            pass


def update_vectordb_settings(
    config: Config, *, vectordb_type: str, vectordb_location: str | None
) -> None:
    """Validate and update VectorDB settings into env and session.

    Basic validation rules follow CLI's behavior:
      - vectordb_type must be 'faiss' or 'pgvector'
      - if type == 'faiss' and location provided: must be an existing directory
      - if type == 'pgvector' and location provided: must start with 'postgresql://'
    """
    vtype = (vectordb_type or "").lower()
    if vtype not in ("faiss", "pgvector"):
        raise ValueError(f"지원하지 않는 VectorDB 타입: {vectordb_type}")

    vloc = vectordb_location or ""
    if vloc:
        if vtype == "faiss":
            path = Path(vloc)
            # 신규 경로 허용: 존재하면 디렉토리인지 확인, 없으면 상위 디렉토리 생성
            if path.exists() and not path.is_dir():
                raise ValueError(
                    f"유효하지 않은 FAISS 디렉토리 경로(파일 경로임): {vloc}"
                )
            if not path.exists():
                try:
                    path.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    raise ValueError(f"FAISS 경로 생성 실패: {vloc} | {e}")
        elif vtype == "pgvector":
            if not vloc.startswith("postgresql://"):
                raise ValueError("pgvector URL은 'postgresql://'로 시작해야 합니다")

    # Persist to runtime config
    config.vectordb_type = vtype
    config.vectordb_location = vloc

    # Reflect to process env for downstream modules
    os.environ["VECTORDB_TYPE"] = vtype
    if vloc:
        os.environ["VECTORDB_LOCATION"] = vloc

    # Reflect to session state for UI
    if st is not None:
        try:
            st.session_state["vectordb_type"] = vtype
            st.session_state["vectordb_location"] = vloc
        except Exception:
            pass
