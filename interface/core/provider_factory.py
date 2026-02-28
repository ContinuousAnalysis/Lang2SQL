"""Settings UI에서 선택된 프로파일을 LLMPort/EmbeddingPort로 변환하는 팩토리.

LLMProfile과 EmbeddingProfile(config/models.py)을 받아
lang2sql.integrations의 구현체를 반환한다.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lang2sql.core.ports import EmbeddingPort, LLMPort
    from interface.core.config.models import EmbeddingProfile, LLMProfile


def build_llm(profile: "LLMProfile") -> "LLMPort":
    """LLMProfile → LLMPort 변환. Settings UI에서 호출한다."""
    f = profile.fields
    provider = profile.provider.lower()

    if provider == "openai":
        from lang2sql.integrations.llm.openai_ import OpenAILLM

        return OpenAILLM(
            model=f.get("model", "gpt-4o"),
            api_key=f.get("api_key"),
        )

    if provider == "anthropic":
        from lang2sql.integrations.llm.anthropic_ import AnthropicLLM

        return AnthropicLLM(
            model=f.get("model", "claude-sonnet-4-6"),
            api_key=f.get("api_key"),
        )

    if provider == "azure":
        from lang2sql.integrations.llm.azure_ import AzureOpenAILLM

        return AzureOpenAILLM(
            azure_deployment=f["azure_deployment"],
            azure_endpoint=f["azure_endpoint"],
            api_version=f.get("api_version", "2023-07-01-preview"),
            api_key=f.get("api_key"),
        )

    if provider == "gemini":
        from lang2sql.integrations.llm.gemini_ import GeminiLLM

        return GeminiLLM(
            model=f.get("model", "gemini-2.0-flash-lite"),
            api_key=f.get("api_key"),
        )

    if provider == "bedrock":
        from lang2sql.integrations.llm.bedrock_ import BedrockLLM

        return BedrockLLM(
            model=f["model"],
            aws_access_key_id=f.get("aws_access_key_id"),
            aws_secret_access_key=f.get("aws_secret_access_key"),
            region_name=f.get("region_name", "us-east-1"),
        )

    if provider == "ollama":
        from lang2sql.integrations.llm.ollama_ import OllamaLLM

        return OllamaLLM(
            model=f["model"],
            base_url=f.get("base_url", "http://localhost:11434"),
        )

    if provider == "huggingface":
        from lang2sql.integrations.llm.huggingface_ import HuggingFaceLLM

        return HuggingFaceLLM(
            repo_id=f.get("repo_id"),
            endpoint_url=f.get("endpoint_url"),
            api_token=f.get("api_token"),
        )

    raise ValueError(f"Unknown LLM provider: {provider!r}")


def build_embedding(profile: "EmbeddingProfile") -> "EmbeddingPort":
    """EmbeddingProfile → EmbeddingPort 변환. Settings UI에서 호출한다."""
    f = profile.fields
    provider = profile.provider.lower()

    if provider == "openai":
        from lang2sql.integrations.embedding.openai_ import OpenAIEmbedding

        return OpenAIEmbedding(
            model=f.get("model", "text-embedding-3-small"),
            api_key=f.get("api_key"),
        )

    if provider == "azure":
        from lang2sql.integrations.embedding.azure_ import AzureOpenAIEmbedding

        return AzureOpenAIEmbedding(
            azure_deployment=f["azure_deployment"],
            azure_endpoint=f["azure_endpoint"],
            api_version=f.get("api_version", "2023-09-15-preview"),
            api_key=f.get("api_key"),
        )

    if provider == "ollama":
        from lang2sql.integrations.embedding.ollama_ import OllamaEmbedding

        return OllamaEmbedding(
            model=f.get("model", "nomic-embed-text"),
            base_url=f.get("base_url", "http://localhost:11434"),
        )

    if provider == "bedrock":
        from lang2sql.integrations.embedding.bedrock_ import BedrockEmbedding

        return BedrockEmbedding(
            model_id=f.get("model_id", "amazon.titan-embed-text-v2:0"),
            aws_access_key_id=f.get("aws_access_key_id"),
            aws_secret_access_key=f.get("aws_secret_access_key"),
            region_name=f.get("region_name", "us-east-1"),
        )

    if provider == "gemini":
        from lang2sql.integrations.embedding.gemini_ import GeminiEmbedding

        return GeminiEmbedding(
            model=f.get("model", "models/embedding-001"),
            api_key=f.get("api_key"),
        )

    if provider == "huggingface":
        from lang2sql.integrations.embedding.huggingface_ import HuggingFaceEmbedding

        return HuggingFaceEmbedding(
            model=f.get("model", f.get("repo_id", "")),
        )

    raise ValueError(f"Unknown embedding provider: {provider!r}")
