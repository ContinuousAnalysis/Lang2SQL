"""Memory V1 — service round trip and inject-all behaviour (★②)."""

from __future__ import annotations

import asyncio

from lang2sql.memory import (
    InMemoryStore,
    InjectAllRecall,
    ManualExtractor,
    MemoryService,
)


def _service() -> MemoryService:
    return MemoryService(InMemoryStore(), InjectAllRecall(), ManualExtractor())


def test_remember_then_recall_round_trip() -> None:
    svc = _service()

    async def run() -> None:
        fact = await svc.remember("u1", "revenue excludes cancelled orders")
        assert fact.id
        assert fact.source == "manual"
        assert fact.ts > 0

        facts = await svc.recall("u1", "anything")
        assert [f.text for f in facts] == ["revenue excludes cancelled orders"]

    asyncio.run(run())


def test_inject_all_returns_every_fact_for_owner() -> None:
    svc = _service()

    async def run() -> None:
        await svc.remember("u1", "fact a")
        await svc.remember("u1", "fact b")
        await svc.remember("u2", "other owner")

        facts = await svc.recall("u1", "ignored query")
        assert {f.text for f in facts} == {"fact a", "fact b"}

    asyncio.run(run())


def test_recall_empty_owner_is_empty_and_renders_blank() -> None:
    svc = _service()

    async def run() -> None:
        facts = await svc.recall("nobody", "q")
        assert facts == []
        assert svc.render(facts) == ""

    asyncio.run(run())


def test_render_produces_markdown_block() -> None:
    svc = _service()

    async def run() -> None:
        await svc.remember("u1", "fact a")
        rendered = svc.render(await svc.recall("u1", "q"))
        assert "## Remembered facts" in rendered
        assert "- fact a" in rendered

    asyncio.run(run())


def test_manual_extractor_yields_nothing() -> None:
    extractor = ManualExtractor()

    async def run() -> None:
        assert await extractor.extract("u1", []) == []

    asyncio.run(run())
