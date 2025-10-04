import os
import streamlit as st

from interface.core.config import (
    update_llm_settings,
    update_embedding_settings,
    Config,
    load_config,
)


LLM_PROVIDERS = [
    "openai",
    "azure",
    "bedrock",
    "gemini",
    "ollama",
    "huggingface",
]


def _llm_fields(provider: str) -> list[tuple[str, str, bool]]:
    """Return list of (label, env_key, is_secret) for LLM provider."""
    p = provider.lower()
    if p == "openai":
        return [
            ("Model", "OPEN_AI_LLM_MODEL", False),
            ("API Key", "OPEN_AI_KEY", True),
        ]
    if p == "azure":
        return [
            ("Endpoint", "AZURE_OPENAI_LLM_ENDPOINT", False),
            ("Deployment(Model)", "AZURE_OPENAI_LLM_MODEL", False),
            ("API Version", "AZURE_OPENAI_LLM_API_VERSION", False),
            ("API Key", "AZURE_OPENAI_LLM_KEY", True),
        ]
    if p == "bedrock":
        return [
            ("Model", "AWS_BEDROCK_LLM_MODEL", False),
            ("Access Key ID", "AWS_BEDROCK_LLM_ACCESS_KEY_ID", True),
            ("Secret Access Key", "AWS_BEDROCK_LLM_SECRET_ACCESS_KEY", True),
            ("Region", "AWS_BEDROCK_LLM_REGION", False),
        ]
    if p == "gemini":
        return [
            ("Model", "GEMINI_LLM_MODEL", False),
            # ChatGoogleGenerativeAI uses GOOGLE_API_KEY at process level, but factory currently reads only model
        ]
    if p == "ollama":
        return [
            ("Model", "OLLAMA_LLM_MODEL", False),
            ("Base URL", "OLLAMA_LLM_BASE_URL", False),
        ]
    if p == "huggingface":
        return [
            ("Endpoint URL", "HUGGING_FACE_LLM_ENDPOINT", False),
            ("Repo ID", "HUGGING_FACE_LLM_REPO_ID", False),
            ("Model", "HUGGING_FACE_LLM_MODEL", False),
            ("API Token", "HUGGING_FACE_LLM_API_TOKEN", True),
        ]
    return []


def _embedding_fields(provider: str) -> list[tuple[str, str, bool]]:
    p = provider.lower()
    if p == "openai":
        return [
            ("Model", "OPEN_AI_EMBEDDING_MODEL", False),
            ("API Key", "OPEN_AI_KEY", True),
        ]
    if p == "azure":
        return [
            ("Endpoint", "AZURE_OPENAI_EMBEDDING_ENDPOINT", False),
            ("Deployment(Model)", "AZURE_OPENAI_EMBEDDING_MODEL", False),
            ("API Version", "AZURE_OPENAI_EMBEDDING_API_VERSION", False),
            ("API Key", "AZURE_OPENAI_EMBEDDING_KEY", True),
        ]
    if p == "bedrock":
        return [
            ("Model", "AWS_BEDROCK_EMBEDDING_MODEL", False),
            ("Access Key ID", "AWS_BEDROCK_EMBEDDING_ACCESS_KEY_ID", True),
            ("Secret Access Key", "AWS_BEDROCK_EMBEDDING_SECRET_ACCESS_KEY", True),
            ("Region", "AWS_BEDROCK_EMBEDDING_REGION", False),
        ]
    if p == "gemini":
        return [
            ("Model", "GEMINI_EMBEDDING_MODEL", False),
            ("API Key", "GEMINI_EMBEDDING_KEY", True),
        ]
    if p == "ollama":
        return [
            ("Model", "OLLAMA_EMBEDDING_MODEL", False),
            ("Base URL", "OLLAMA_EMBEDDING_BASE_URL", False),
        ]
    if p == "huggingface":
        return [
            ("Model", "HUGGING_FACE_EMBEDDING_MODEL", False),
            ("Repo ID", "HUGGING_FACE_EMBEDDING_REPO_ID", False),
            ("API Token", "HUGGING_FACE_EMBEDDING_API_TOKEN", True),
        ]
    return []


def render_llm_section(config: Config | None = None) -> None:
    st.subheader("LLM 설정")

    if config is None:
        try:
            config = load_config()
        except Exception:
            config = None  # UI 일관성을 위한 옵셔널 처리

    llm_col, emb_col = st.columns(2)

    with llm_col:
        st.markdown("**Chat LLM**")
        default_llm_provider = (
            (
                st.session_state.get("LLM_PROVIDER")
                or os.getenv("LLM_PROVIDER")
                or "openai"
            )
        ).lower()
        try:
            default_llm_index = LLM_PROVIDERS.index(default_llm_provider)
        except ValueError:
            default_llm_index = 0
        provider = st.selectbox(
            "공급자",
            options=LLM_PROVIDERS,
            index=default_llm_index,
            key="llm_provider",
        )
        fields = _llm_fields(provider)
        values: dict[str, str | None] = {}
        for label, env_key, is_secret in fields:
            prefill = st.session_state.get(env_key) or os.getenv(env_key) or ""
            if is_secret:
                values[env_key] = st.text_input(
                    label, value=prefill, type="password", key=f"llm_{env_key}"
                )
            else:
                values[env_key] = st.text_input(
                    label, value=prefill, key=f"llm_{env_key}"
                )

        # 메시지 영역: 버튼 컬럼 밖(섹션 폭)으로 배치하여 좁은 폭에 눌려 깨지는 문제 방지
        llm_msg = st.empty()

        save_cols = st.columns([1, 1, 2])
        with save_cols[0]:
            if st.button("저장", key="llm_save"):
                try:
                    update_llm_settings(provider=provider, values=values)
                    llm_msg.success("LLM 설정이 저장되었습니다.")
                except Exception as e:
                    llm_msg.error(f"저장 실패: {e}")
        with save_cols[1]:
            if st.button("검증", key="llm_validate"):
                # 가벼운 검증: 필수 키 존재 여부만 확인
                try:
                    update_llm_settings(provider=provider, values=values)
                    llm_msg.success(
                        "형식 검증 완료. 실제 호출은 실행 경로에서 재검증됩니다."
                    )
                except Exception as e:
                    llm_msg.error(f"검증 실패: {e}")

    with emb_col:
        st.markdown("**Embeddings**")
        default_emb_provider = (
            (
                st.session_state.get("EMBEDDING_PROVIDER")
                or os.getenv("EMBEDDING_PROVIDER")
                or "openai"
            )
        ).lower()
        try:
            default_emb_index = LLM_PROVIDERS.index(default_emb_provider)
        except ValueError:
            default_emb_index = 0
        e_provider = st.selectbox(
            "공급자",
            options=LLM_PROVIDERS,
            index=default_emb_index,
            key="embedding_provider",
        )
        e_fields = _embedding_fields(e_provider)
        e_values: dict[str, str | None] = {}
        for label, env_key, is_secret in e_fields:
            prefill = st.session_state.get(env_key) or os.getenv(env_key) or ""
            if is_secret:
                e_values[env_key] = st.text_input(
                    label, value=prefill, type="password", key=f"emb_{env_key}"
                )
            else:
                e_values[env_key] = st.text_input(
                    label, value=prefill, key=f"emb_{env_key}"
                )

        # 메시지 영역: 버튼 컬럼 밖(섹션 폭)
        emb_msg = st.empty()

        e_cols = st.columns([1, 1, 2])
        with e_cols[0]:
            if st.button("저장", key="emb_save"):
                try:
                    update_embedding_settings(provider=e_provider, values=e_values)
                    emb_msg.success("Embeddings 설정이 저장되었습니다.")
                except Exception as e:
                    emb_msg.error(f"저장 실패: {e}")
        with e_cols[1]:
            if st.button("검증", key="emb_validate"):
                try:
                    update_embedding_settings(provider=e_provider, values=e_values)
                    emb_msg.success("형식 검증 완료.")
                except Exception as e:
                    emb_msg.error(f"검증 실패: {e}")
