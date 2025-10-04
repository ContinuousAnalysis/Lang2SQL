import streamlit as st

from infra.monitoring.check_server import CheckServer
from interface.core.config import (
    Config,
    load_config,
    update_datahub_server,
    update_vectordb_settings,
    update_data_source_mode,
)


def _render_status_banner(config: Config) -> None:
    mode = config.data_source_mode
    ready_msgs = []

    if mode == "datahub":
        is_ok = CheckServer.is_gms_server_healthy(url=config.datahub_server)
        if is_ok:
            st.success(f"데이터 소스 준비됨: DataHub ({config.datahub_server})")
        else:
            st.warning(
                "DataHub 헬스 체크 실패. URL을 확인하거나 VectorDB로 전환하세요."
            )
    elif mode == "vectordb":
        if config.vectordb_type and (
            (config.vectordb_type == "faiss" and config.vectordb_location)
            or (config.vectordb_type == "pgvector" and config.vectordb_location)
        ):
            st.success(
                f"데이터 소스 준비됨: VectorDB ({config.vectordb_type}, {config.vectordb_location or '기본값'})"
            )
        else:
            st.warning("VectorDB 설정이 불완전합니다. 타입/위치를 확인하세요.")
    else:
        st.info(
            "데이터 소스를 선택해주세요: DataHub 또는 VectorDB 중 하나는 필수입니다."
        )


def render_data_source_section(config: Config | None = None) -> None:
    st.subheader("데이터 소스 (필수)")

    if config is None:
        config = load_config()

    _render_status_banner(config)

    # 선택 스위치
    col = st.columns([1, 3])[0]
    with col:
        mode = st.radio(
            "데이터 소스 선택",
            options=["DataHub", "VectorDB"],
            horizontal=True,
            index=(
                0 if (config.data_source_mode or "datahub").lower() == "datahub" else 1
            ),
        )
    selected = mode.lower()
    update_data_source_mode(config, selected)

    st.divider()

    if selected == "datahub":
        with st.container(border=True):
            url = st.text_input(
                "DataHub GMS 서버 URL",
                value=config.datahub_server,
                placeholder="http://localhost:8080",
                help="예: http://localhost:8080",
            )

            cols = st.columns([1, 1, 2])
            with cols[0]:
                if st.button("헬스 체크", key="ds_health"):
                    ok = CheckServer.is_gms_server_healthy(url=url)
                    if ok:
                        st.success("GMS 서버가 정상입니다.")
                    else:
                        st.error(
                            "GMS 서버 헬스 체크 실패. URL과 네트워크를 확인하세요."
                        )

            with cols[1]:
                if st.button("저장", key="ds_save"):
                    if not url:
                        st.warning("URL을 입력하세요.")
                    else:
                        ok = CheckServer.is_gms_server_healthy(url=url)
                        if not ok:
                            st.error("저장 실패: 헬스 체크가 통과되지 않았습니다.")
                        else:
                            try:
                                update_datahub_server(config, url)
                                st.success(
                                    "저장되었습니다. 현재 세션에 즉시 반영됩니다."
                                )
                            except Exception:
                                st.error(
                                    "설정 적용 중 오류가 발생했습니다. 로그를 확인하세요."
                                )

    else:  # VectorDB
        with st.container(border=True):
            vtype = st.selectbox(
                "VectorDB 타입",
                options=["faiss", "pgvector"],
                index=0 if (config.vectordb_type or "faiss") == "faiss" else 1,
            )

            placeholder_text = (
                "FAISS 디렉토리 경로 (예: ./dev/table_info_db)"
                if vtype == "faiss"
                else "pgvector 연결 문자열 (postgresql://user:pass@host:port/db)"
            )

            vloc = st.text_input(
                "VectorDB 위치",
                value=config.vectordb_location,
                placeholder=placeholder_text,
                help=placeholder_text,
            )

            cols = st.columns([1, 1, 2])
            with cols[0]:
                if st.button("검증", key="vdb_validate"):
                    try:
                        update_vectordb_settings(
                            config, vectordb_type=vtype, vectordb_location=vloc
                        )
                        st.success("VectorDB 설정이 유효합니다.")
                    except Exception as e:
                        st.error(f"검증 실패: {e}")

            with cols[1]:
                if st.button("저장", key="vdb_save"):
                    try:
                        update_vectordb_settings(
                            config, vectordb_type=vtype, vectordb_location=vloc
                        )
                        st.success("저장되었습니다. 현재 세션에 즉시 반영됩니다.")
                    except Exception as e:
                        st.error(f"저장 실패: {e}")
