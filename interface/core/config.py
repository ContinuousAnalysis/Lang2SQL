from dataclasses import dataclass
import os
from pathlib import Path

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
            if not path.exists() or not path.is_dir():
                raise ValueError(f"유효하지 않은 FAISS 디렉토리 경로: {vloc}")
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
