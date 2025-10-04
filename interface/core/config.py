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


# ---- DB Connections registry (non-sensitive persistence) ----


@dataclass
class DBConnectionProfile:
    name: str
    type: str  # 'postgresql' | 'mysql' | 'mariadb' | 'oracle' | 'clickhouse' | 'duckdb' | 'sqlite' | 'databricks' | 'snowflake' | 'trino'
    host: Optional[str] = None
    port: Optional[int] = None
    user: Optional[str] = None
    password: Optional[str] = None
    database: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None  # non-secret
    note: Optional[str] = None


@dataclass
class DBConnectionsRegistry:
    connections: List[DBConnectionProfile] = field(default_factory=list)


# ---- LLM profiles registry (non-sensitive persistence) ----


@dataclass
class LLMProfile:
    name: str
    provider: (
        str  # 'openai' | 'azure' | 'bedrock' | 'gemini' | 'ollama' | 'huggingface'
    )
    fields: Dict[str, str] = field(default_factory=dict)  # includes secrets
    note: Optional[str] = None


@dataclass
class LLMRegistry:
    profiles: List[LLMProfile] = field(default_factory=list)


# ---- Embedding profiles registry (includes secrets) ----


@dataclass
class EmbeddingProfile:
    name: str
    provider: (
        str  # 'openai' | 'azure' | 'bedrock' | 'gemini' | 'ollama' | 'huggingface'
    )
    fields: Dict[str, str] = field(default_factory=dict)
    note: Optional[str] = None


@dataclass
class EmbeddingRegistry:
    profiles: List[EmbeddingProfile] = field(default_factory=list)


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


def get_db_connections_registry() -> DBConnectionsRegistry:
    if st is not None and "db_connections_registry" in st.session_state:
        reg = st.session_state["db_connections_registry"]
        return reg  # stored as DBConnectionsRegistry
    try:
        registry = load_db_registry_from_disk()
    except Exception:
        registry = DBConnectionsRegistry()
    if st is not None:
        st.session_state["db_connections_registry"] = registry
    return registry


def _save_registry(registry: DataSourcesRegistry) -> None:
    if st is not None:
        st.session_state["data_sources_registry"] = registry
    try:
        save_registry_to_disk(registry)
    except Exception:
        # fail-soft; UI will still have session copy
        pass


def _save_db_registry(registry: DBConnectionsRegistry) -> None:
    if st is not None:
        st.session_state["db_connections_registry"] = registry
    try:
        save_db_registry_to_disk(registry)
    except Exception:
        # fail-soft; UI will still have session copy
        pass


def get_llm_registry() -> LLMRegistry:
    if st is not None and "llm_registry" in st.session_state:
        return st.session_state["llm_registry"]
    try:
        registry = load_llm_registry_from_disk()
    except Exception:
        registry = LLMRegistry()
    if st is not None:
        st.session_state["llm_registry"] = registry
    return registry


def _save_llm_registry(registry: LLMRegistry) -> None:
    if st is not None:
        st.session_state["llm_registry"] = registry
    try:
        save_llm_registry_to_disk(registry)
    except Exception:
        pass


def get_embedding_registry() -> EmbeddingRegistry:
    if st is not None and "embedding_registry" in st.session_state:
        return st.session_state["embedding_registry"]
    try:
        registry = load_embedding_registry_from_disk()
    except Exception:
        registry = EmbeddingRegistry()
    if st is not None:
        st.session_state["embedding_registry"] = registry
    return registry


def _save_embedding_registry(registry: EmbeddingRegistry) -> None:
    if st is not None:
        st.session_state["embedding_registry"] = registry
    try:
        save_embedding_registry_to_disk(registry)
    except Exception:
        pass


# ---- Disk persistence for registry ----


def _get_registry_file_path() -> Path:
    # Allow override via env var, else default to ./config/data_sources.json
    override = os.getenv("LANG2SQL_REGISTRY_PATH")
    if override:
        return Path(override).expanduser().resolve()
    return Path(os.getcwd()) / "config" / "data_sources.json"


def _get_db_registry_file_path() -> Path:
    # Allow override via env var, else default to ./config/db_connections.json
    override = os.getenv("LANG2SQL_DB_REGISTRY_PATH")
    if override:
        return Path(override).expanduser().resolve()
    return Path(os.getcwd()) / "config" / "db_connections.json"


def _get_llm_registry_file_path() -> Path:
    override = os.getenv("LANG2SQL_LLM_REGISTRY_PATH")
    if override:
        return Path(override).expanduser().resolve()
    return Path(os.getcwd()) / "config" / "llm_profiles.json"


def _get_embedding_registry_file_path() -> Path:
    override = os.getenv("LANG2SQL_EMBEDDING_REGISTRY_PATH")
    if override:
        return Path(override).expanduser().resolve()
    return Path(os.getcwd()) / "config" / "embedding_profiles.json"


def _ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def save_registry_to_disk(registry: DataSourcesRegistry) -> None:
    path = _get_registry_file_path()
    _ensure_parent_dir(path)
    payload = asdict(registry)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def save_db_registry_to_disk(registry: DBConnectionsRegistry) -> None:
    path = _get_db_registry_file_path()
    _ensure_parent_dir(path)
    payload = asdict(registry)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def save_llm_registry_to_disk(registry: LLMRegistry) -> None:
    path = _get_llm_registry_file_path()
    _ensure_parent_dir(path)
    payload = asdict(registry)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def save_embedding_registry_to_disk(registry: EmbeddingRegistry) -> None:
    path = _get_embedding_registry_file_path()
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


def _parse_db_conn_list(items: List[Dict[str, Any]]) -> List[DBConnectionProfile]:
    parsed: List[DBConnectionProfile] = []
    for item in items or []:
        name = str(item.get("name", "")).strip()
        db_type = str(item.get("type", "")).strip().lower()
        if not name or not db_type:
            continue
        host = item.get("host")
        port = item.get("port")
        try:
            port = int(port) if port is not None else None
        except Exception:
            port = None
        user = item.get("user")
        password = item.get("password")
        database = item.get("database")
        extra = item.get("extra") or None
        note = item.get("note") or None
        parsed.append(
            DBConnectionProfile(
                name=name,
                type=db_type,
                host=host,
                port=port,
                user=user,
                password=password,
                database=database,
                extra=extra,
                note=note,
            )
        )
    return parsed


def load_db_registry_from_disk() -> DBConnectionsRegistry:
    path = _get_db_registry_file_path()
    if not path.exists():
        return DBConnectionsRegistry()
    with path.open("r", encoding="utf-8") as f:
        data: Dict[str, Any] = json.load(f)
    return DBConnectionsRegistry(
        connections=_parse_db_conn_list(data.get("connections", []))
    )


def _parse_llm_profiles(items: List[Dict[str, Any]]) -> List[LLMProfile]:
    parsed: List[LLMProfile] = []
    for item in items or []:
        name = str(item.get("name", "")).strip()
        provider = str(item.get("provider", "")).strip().lower()
        if not name or not provider:
            continue
        fields = item.get("fields") or {}
        note = item.get("note") or None
        if not isinstance(fields, dict):
            fields = {}
        parsed.append(
            LLMProfile(name=name, provider=provider, fields=fields, note=note)
        )
    return parsed


def load_llm_registry_from_disk() -> LLMRegistry:
    path = _get_llm_registry_file_path()
    if not path.exists():
        return LLMRegistry()
    with path.open("r", encoding="utf-8") as f:
        data: Dict[str, Any] = json.load(f)
    return LLMRegistry(profiles=_parse_llm_profiles(data.get("profiles", [])))


def _parse_embedding_profiles(items: List[Dict[str, Any]]) -> List[EmbeddingProfile]:
    parsed: List[EmbeddingProfile] = []
    for item in items or []:
        name = str(item.get("name", "")).strip()
        provider = str(item.get("provider", "")).strip().lower()
        if not name or not provider:
            continue
        fields = item.get("fields") or {}
        note = item.get("note") or None
        if not isinstance(fields, dict):
            fields = {}
        parsed.append(
            EmbeddingProfile(name=name, provider=provider, fields=fields, note=note)
        )
    return parsed


def load_embedding_registry_from_disk() -> EmbeddingRegistry:
    path = _get_embedding_registry_file_path()
    if not path.exists():
        return EmbeddingRegistry()
    with path.open("r", encoding="utf-8") as f:
        data: Dict[str, Any] = json.load(f)
    return EmbeddingRegistry(
        profiles=_parse_embedding_profiles(data.get("profiles", []))
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


# ---- DB Connections registry ops ----


def add_db_connection(
    *,
    name: str,
    db_type: str,
    host: Optional[str] = None,
    port: Optional[int] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    database: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
    note: Optional[str] = None,
) -> None:
    db_type_norm = (db_type or "").lower()
    registry = get_db_connections_registry()
    if any(c.name == name for c in registry.connections):
        raise ValueError(f"이미 존재하는 DB 프로파일 이름입니다: {name}")
    registry.connections.append(
        DBConnectionProfile(
            name=name,
            type=db_type_norm,
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            extra=extra or None,
            note=note or None,
        )
    )
    _save_db_registry(registry)


def update_db_connection(
    *,
    name: str,
    db_type: str,
    host: Optional[str],
    port: Optional[int],
    user: Optional[str],
    password: Optional[str],
    database: Optional[str],
    extra: Optional[Dict[str, Any]],
    note: Optional[str],
) -> None:
    db_type_norm = (db_type or "").lower()
    registry = get_db_connections_registry()
    for idx, c in enumerate(registry.connections):
        if c.name == name:
            registry.connections[idx] = DBConnectionProfile(
                name=name,
                type=db_type_norm,
                host=host,
                port=port,
                user=user,
                password=password,
                database=database,
                extra=extra or None,
                note=note or None,
            )
            _save_db_registry(registry)
            return
    raise ValueError(f"존재하지 않는 DB 프로파일 이름입니다: {name}")


def delete_db_connection(*, name: str) -> None:
    registry = get_db_connections_registry()
    registry.connections = [c for c in registry.connections if c.name != name]
    _save_db_registry(registry)


# ---- DB env/session update (secrets-only in-memory) ----


def update_db_settings(
    *,
    db_type: str,
    values: Dict[str, Any] | None,
    secrets: Dict[str, Optional[str]] | None = None,
) -> None:
    """Update DB settings into process env and session.

    Only non-sensitive values should be passed in values and may come from registry.
    Secrets (e.g., PASSWORD, ACCESS_TOKEN) are applied to env/session but never persisted to disk.
    """
    db_type_norm = (db_type or "").lower()
    if not db_type_norm:
        raise ValueError("DB 타입이 비어 있습니다.")

    # Core selector
    _put_env("DB_TYPE", db_type_norm)
    _put_session("DB_TYPE", db_type_norm)

    prefix = db_type_norm.upper()

    base_keys = ["HOST", "PORT", "USER", "DATABASE"]
    for base_key in base_keys:
        vk = base_key.lower()
        v = (values or {}).get(vk)
        if v is None:
            continue
        _put_env(f"{prefix}_{base_key}", str(v))
        _put_session(f"{prefix}_{base_key}", str(v))

    # Extras (non-secret)
    extra = (values or {}).get("extra") or {}
    if isinstance(extra, dict):
        for k, v in extra.items():
            if v is None:
                continue
            _put_env(f"{prefix}_{str(k).upper()}", str(v))
            _put_session(f"{prefix}_{str(k).upper()}", str(v))

    # Secrets (applied to env+session, never persisted)
    for sk, sv in (secrets or {}).items():
        if sv is None:
            continue
        key_up = str(sk).upper()
        _put_env(f"{prefix}_{key_up}", str(sv))
        _put_session(f"{prefix}_{key_up}", str(sv))


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


# ---- LLM & Embeddings helpers ----


def _put_env(key: str, value: str | None) -> None:
    if value is None:
        return
    os.environ[key] = value


def _put_session(key: str, value: str | None) -> None:
    if st is None:
        return
    try:
        st.session_state[key] = value
    except Exception:
        pass


def update_llm_settings(*, provider: str, values: dict[str, str | None]) -> None:
    """Update chat LLM settings from UI into process env and session.

    This function mirrors the environment-variable based configuration consumed by
    llm_utils.llm.factory.get_llm(). Only sets provided keys; missing values are left as-is.
    """
    provider_norm = (provider or "").lower()
    if provider_norm not in {
        "openai",
        "azure",
        "bedrock",
        "gemini",
        "ollama",
        "huggingface",
    }:
        raise ValueError(f"지원하지 않는 LLM 공급자: {provider}")

    # Core selector
    _put_env("LLM_PROVIDER", provider_norm)
    _put_session("LLM_PROVIDER", provider_norm)

    # Provider-specific fields (keys exactly as factory expects)
    for k, v in (values or {}).items():
        if v is not None:
            _put_env(k, v)
            _put_session(k, v)


def save_llm_profile(
    *,
    name: str,
    provider: str,
    values: dict[str, str | None],
    note: Optional[str] = None,
) -> None:
    """Persist an LLM profile including secrets (explicit per user's request)."""
    provider_norm = (provider or "").lower()
    stored_fields: Dict[str, str] = {}
    for k, v in (values or {}).items():
        if v is None:
            continue
        stored_fields[k] = str(v)

    reg = get_llm_registry()
    # upsert by name
    for idx, p in enumerate(reg.profiles):
        if p.name == name:
            reg.profiles[idx] = LLMProfile(
                name=name, provider=provider_norm, fields=stored_fields, note=note
            )
            _save_llm_registry(reg)
            return
    reg.profiles.append(
        LLMProfile(name=name, provider=provider_norm, fields=stored_fields, note=note)
    )
    _save_llm_registry(reg)


def update_embedding_settings(*, provider: str, values: dict[str, str | None]) -> None:
    """Update Embeddings settings from UI into process env and session.

    Mirrors env vars consumed by llm_utils.llm.factory.get_embeddings().
    """
    provider_norm = (provider or "").lower()
    if provider_norm not in {
        "openai",
        "azure",
        "bedrock",
        "gemini",
        "ollama",
        "huggingface",
    }:
        raise ValueError(f"지원하지 않는 Embedding 공급자: {provider}")

    _put_env("EMBEDDING_PROVIDER", provider_norm)
    _put_session("EMBEDDING_PROVIDER", provider_norm)

    for k, v in (values or {}).items():
        if v is not None:
            _put_env(k, v)
            _put_session(k, v)


def save_embedding_profile(
    *,
    name: str,
    provider: str,
    values: dict[str, str | None],
    note: Optional[str] = None,
) -> None:
    provider_norm = (provider or "").lower()
    stored_fields: Dict[str, str] = {}
    for k, v in (values or {}).items():
        if v is None:
            continue
        stored_fields[k] = str(v)

    reg = get_embedding_registry()
    for idx, p in enumerate(reg.profiles):
        if p.name == name:
            reg.profiles[idx] = EmbeddingProfile(
                name=name, provider=provider_norm, fields=stored_fields, note=note
            )
            _save_embedding_registry(reg)
            return
    reg.profiles.append(
        EmbeddingProfile(
            name=name, provider=provider_norm, fields=stored_fields, note=note
        )
    )
    _save_embedding_registry(reg)
