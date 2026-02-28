from .factory import build_db_from_env, build_embedding_from_env, build_llm_from_env
from .components.enrichment.context_enricher import ContextEnricher
from .components.enrichment.question_profiler import QuestionProfiler
from .components.execution.sql_executor import SQLExecutor
from .components.gate.question_gate import QuestionGate
from .components.gate.table_suitability import TableSuitabilityEvaluator
from .components.generation.sql_generator import SQLGenerator
from .components.loaders.directory_ import DirectoryLoader
from .components.loaders.markdown_ import MarkdownLoader
from .components.loaders.plaintext_ import PlainTextLoader
from .components.retrieval.chunker import (
    CatalogChunker,
    DocumentChunkerPort,
    RecursiveCharacterChunker,
)
from .components.retrieval.hybrid import HybridRetriever
from .components.retrieval.keyword import KeywordRetriever
from .components.retrieval.vector import VectorRetriever
from .core.catalog import (
    CatalogEntry,
    GateResult,
    IndexedChunk,
    QuestionProfile,
    RetrievalResult,
    TableScore,
    TextDocument,
)
from .core.exceptions import ComponentError, IntegrationMissingError, Lang2SQLError
from .core.hooks import MemoryHook, NullHook, TraceHook
from .core.ports import (
    DBPort,
    DocumentLoaderPort,
    EmbeddingPort,
    LLMPort,
    VectorStorePort,
)
from .flows.enriched_nl2sql import EnrichedNL2SQL
from .flows.hybrid import HybridNL2SQL
from .flows.nl2sql import BaselineNL2SQL
from .integrations.catalog.datahub_ import DataHubCatalogLoader
from .integrations.embedding.azure_ import AzureOpenAIEmbedding
from .integrations.embedding.bedrock_ import BedrockEmbedding
from .integrations.embedding.gemini_ import GeminiEmbedding
from .integrations.embedding.huggingface_ import HuggingFaceEmbedding
from .integrations.embedding.ollama_ import OllamaEmbedding
from .integrations.llm.azure_ import AzureOpenAILLM
from .integrations.llm.bedrock_ import BedrockLLM
from .integrations.llm.gemini_ import GeminiLLM
from .integrations.llm.huggingface_ import HuggingFaceLLM
from .integrations.llm.ollama_ import OllamaLLM
from .integrations.vectorstore.faiss_ import FAISSVectorStore
from .integrations.vectorstore.pgvector_ import PGVectorStore

__all__ = [
    # Data types
    "CatalogEntry",
    "TextDocument",
    "IndexedChunk",
    "RetrievalResult",
    # Domain types (Phase 4)
    "GateResult",
    "QuestionProfile",
    "TableScore",
    # Ports (protocols)
    "LLMPort",
    "DBPort",
    "EmbeddingPort",
    "VectorStorePort",
    "DocumentLoaderPort",
    # Components — retrieval
    "KeywordRetriever",
    "VectorRetriever",
    "HybridRetriever",
    "DocumentChunkerPort",
    "CatalogChunker",
    "RecursiveCharacterChunker",
    # Components — generation & execution
    "SQLGenerator",
    "SQLExecutor",
    # Components — gate (Phase 4)
    "QuestionGate",
    "TableSuitabilityEvaluator",
    # Components — enrichment (Phase 4)
    "QuestionProfiler",
    "ContextEnricher",
    # Components — loaders
    "MarkdownLoader",
    "PlainTextLoader",
    "DirectoryLoader",
    # Flows
    "BaselineNL2SQL",
    "HybridNL2SQL",
    "EnrichedNL2SQL",
    # Hooks
    "TraceHook",
    "MemoryHook",
    "NullHook",
    # Exceptions
    "Lang2SQLError",
    "ComponentError",
    "IntegrationMissingError",
    # Vector store backends
    "FAISSVectorStore",
    "PGVectorStore",
    # LLM integrations (Phase 1)
    "AzureOpenAILLM",
    "BedrockLLM",
    "GeminiLLM",
    "HuggingFaceLLM",
    "OllamaLLM",
    # Embedding integrations (Phase 2)
    "AzureOpenAIEmbedding",
    "BedrockEmbedding",
    "GeminiEmbedding",
    "HuggingFaceEmbedding",
    "OllamaEmbedding",
    # Catalog integrations (Phase 3)
    "DataHubCatalogLoader",
    # Factory (Phase 6)
    "build_llm_from_env",
    "build_embedding_from_env",
    "build_db_from_env",
]
