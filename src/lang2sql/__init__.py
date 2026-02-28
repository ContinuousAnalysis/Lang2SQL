from .integrations.vectorstore.faiss_ import FAISSVectorStore
from .integrations.vectorstore.pgvector_ import PGVectorStore
from .components.execution.sql_executor import SQLExecutor
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
from .core.catalog import CatalogEntry, IndexedChunk, RetrievalResult, TextDocument
from .core.exceptions import ComponentError, IntegrationMissingError, Lang2SQLError
from .core.hooks import MemoryHook, NullHook, TraceHook
from .core.ports import (
    DBPort,
    DocumentLoaderPort,
    EmbeddingPort,
    LLMPort,
    VectorStorePort,
)
from .flows.hybrid import HybridNL2SQL
from .flows.nl2sql import BaselineNL2SQL

__all__ = [
    # Data types
    "CatalogEntry",
    "TextDocument",
    "IndexedChunk",
    "RetrievalResult",
    # Ports (protocols)
    "LLMPort",
    "DBPort",
    "EmbeddingPort",
    "VectorStorePort",
    "DocumentLoaderPort",
    # Components
    "KeywordRetriever",
    "VectorRetriever",
    "HybridRetriever",
    "DocumentChunkerPort",
    "CatalogChunker",
    "RecursiveCharacterChunker",
    "SQLGenerator",
    "SQLExecutor",
    "MarkdownLoader",
    "PlainTextLoader",
    "DirectoryLoader",
    # Flows
    "BaselineNL2SQL",
    "HybridNL2SQL",
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
]
