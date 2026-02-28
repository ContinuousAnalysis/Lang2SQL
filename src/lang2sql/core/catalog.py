from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypedDict


class CatalogEntry(TypedDict, total=False):
    name: str
    description: str
    columns: dict[str, str]


class TextDocument(TypedDict, total=False):
    """Business document — data dictionaries, business rules, FAQ, etc."""

    id: str  # Unique identifier (required)
    title: str  # Document title (required)
    content: str  # Full body text (required)
    source: str  # File path, URL, etc. (optional)
    metadata: dict  # Free-form additional info (optional)


class IndexedChunk(TypedDict):
    """Minimum indexing unit stored in the vector store. Shared by catalog and document chunks."""

    chunk_id: str  # e.g. "orders__0", "orders__col_1", "bizrule__2"
    text: str  # Text to embed
    source_type: str  # "catalog" | "document"
    source_id: str  # Table name (catalog) or doc id (document)
    chunk_index: int  # Position within the source (0-based)
    metadata: dict  # catalog → full CatalogEntry / document → document meta


@dataclass
class RetrievalResult:
    """Return value of VectorRetriever — schema list + domain context."""

    schemas: list[CatalogEntry] = field(default_factory=list)
    context: list[str] = field(default_factory=list)


@dataclass
class GateResult:
    """QuestionGate 컴포넌트의 반환 타입."""

    suitable: bool
    reason: str
    missing_entities: list[str] = field(default_factory=list)
    requires_data_science: bool = False


@dataclass
class QuestionProfile:
    """질문 특성 프로파일."""

    is_timeseries: bool = False
    is_aggregation: bool = False
    has_filter: bool = False
    is_grouped: bool = False
    has_ranking: bool = False
    has_temporal_comparison: bool = False
    intent_type: str = "lookup"  # trend | lookup | comparison | distribution


@dataclass
class TableScore:
    """개별 테이블의 적합도 평가 결과."""

    table_name: str
    score: float
    reason: str
    matched_columns: list[str] = field(default_factory=list)
    missing_entities: list[str] = field(default_factory=list)
