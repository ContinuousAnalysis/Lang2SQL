"""ContextConcierge — the assembly point that builds one HarnessContext.

This is the only module allowed to import the concrete semantic/safety/adapter
classes; everywhere else depends on the ``core.ports`` Protocols. Per request it
picks an LLM (OpenAI when keyed, else the FakeLLM), restores or starts a
:class:`Session`, and wires the explorer, safety pipeline, scope resolver, and
audit store into a :class:`HarnessContext` for the loop.

Dependency-injection friendly: every collaborator can be overridden in the
ctor so tests (and v1.5 swaps) need no network and no globals.
"""

from __future__ import annotations

import os

from ..adapters.db.postgres_explorer import PostgresExplorer
from ..adapters.llm.fake import FakeLLM
from ..adapters.llm.openai_ import OpenAILLM
from ..adapters.storage.sqlite_store import SqliteStore
from ..core.identity import Identity
from ..core.ports.audit import AuditPort
from ..core.ports.explorer import ExplorerPort
from ..core.ports.llm import LLMPort
from ..core.ports.safety import SafetyPipelinePort
from ..core.ports.semantic_scope import ScopeResolverPort
from ..harness.context import HarnessContext
from ..harness.session import Session
from ..harness.tool_registry import ToolRegistry
from ..ingestion import FileSource, IngestionPipeline, LLMExtractor
from ..memory import InjectAllRecall, InMemoryStore, ManualExtractor, MemoryService
from ..safety.pipeline import SafetyPipeline
from ..tools import build_default_tools
from .scope_resolver import ScopeResolver

# DSN used for the V1 explorer stub when a scope has registered none yet.
_DEFAULT_DSN = "postgresql://stub/v1"


class ContextConcierge:
    """Assembles per-request :class:`HarnessContext` from injected ports."""

    def __init__(
        self,
        *,
        store: SqliteStore | None = None,
        llm: LLMPort | None = None,
        explorer: ExplorerPort | None = None,
        safety: SafetyPipelinePort | None = None,
        scope_resolver: ScopeResolverPort | None = None,
        audit: AuditPort | None = None,
        max_turns: int = 8,
    ) -> None:
        self._store = store if store is not None else SqliteStore()
        # Audit + session persistence both ride the one sqlite store by default.
        self._llm = llm if llm is not None else _default_llm()
        self._explorer = explorer if explorer is not None else PostgresExplorer(_DEFAULT_DSN)
        self._safety = safety if safety is not None else SafetyPipeline()
        self._scope_resolver = (
            scope_resolver if scope_resolver is not None else ScopeResolver()
        )
        self._audit = audit if audit is not None else self._store
        self._max_turns = max_turns

        # V1 memory (in-memory + inject-all + manual) and ingestion (file × LLM).
        self._memory = MemoryService(InMemoryStore(), InjectAllRecall(), ManualExtractor())
        self._ingestion = IngestionPipeline()
        self._source = FileSource()
        self._extractor = LLMExtractor(self._llm)

    @property
    def store(self) -> SqliteStore:
        return self._store

    async def build_context(
        self, identity: Identity, user_text: str | None = None
    ) -> HarnessContext:
        session = await self._store.load(identity.session_key())
        if session is None:
            session = Session(identity=identity)

        tools = ToolRegistry(
            build_default_tools(
                memory=self._memory,
                ingestion=self._ingestion,
                source=self._source,
                extractor=self._extractor,
            )
        )

        return HarnessContext(
            identity=identity,
            llm=self._llm,
            tools=tools,
            session=session,
            explorer=self._explorer,
            safety=self._safety,
            audit=self._audit,
            scope_resolver=self._scope_resolver,
            max_turns=self._max_turns,
        )


def _default_llm() -> LLMPort:
    """OpenAI when a key is present, otherwise the offline FakeLLM."""
    if os.environ.get("OPENAI_API_KEY"):
        return OpenAILLM()
    return FakeLLM()
