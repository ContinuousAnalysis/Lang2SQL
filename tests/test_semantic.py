"""Tests for the semantic federation layer (★④).

Plain functions named ``test_*`` — runnable without pytest via the validation
one-liner in the spawn brief.
"""

from __future__ import annotations

import asyncio

from lang2sql.core.identity import Identity, Scope, ScopeLevel
from lang2sql.semantic import (
    Metric,
    SemanticEntry,
    SemanticKind,
    SemanticLayer,
    SemanticStore,
    merge_scoped,
)
from lang2sql.tenancy.scope_resolver import ScopeResolver


def test_render_empty_is_blank() -> None:
    assert SemanticLayer().render() == ""


def test_render_lists_entries() -> None:
    layer = SemanticLayer(
        [
            SemanticEntry(SemanticKind.METRIC, "active_user", "30d login"),
            SemanticEntry(
                SemanticKind.DIMENSION, "region", "billing country", applies_to="users"
            ),
        ]
    )
    rendered = layer.render()
    assert "**active_user** [metric]: 30d login" in rendered
    assert "**region** [dimension]: billing country (applies to users)" in rendered
    # one bullet line per entry
    assert len(rendered.splitlines()) == 2
    assert all(line.startswith("- ") for line in rendered.splitlines())


def test_layer_add_replaces_same_name() -> None:
    layer = SemanticLayer([SemanticEntry(SemanticKind.METRIC, "rev", "gross")])
    layer.add(SemanticEntry(SemanticKind.METRIC, "rev", "net"))
    assert len(layer.entries) == 1
    assert layer.lookup("rev").definition == "net"


def test_scoped_merge_narrow_wins() -> None:
    """active_user defined at channel must override the guild definition."""
    guild = Scope(ScopeLevel.GUILD, "g1")
    channel = Scope(ScopeLevel.CHANNEL, "c1")
    merged = merge_scoped(
        [
            (channel, [Metric(name="active_user", definition="7d core action")]),
            (guild, [Metric(name="active_user", definition="30d login")]),
        ]
    )
    assert merged.lookup("active_user").definition == "7d core action"


def test_scoped_merge_wider_fills_gaps() -> None:
    guild = Scope(ScopeLevel.GUILD, "g1")
    channel = Scope(ScopeLevel.CHANNEL, "c1")
    merged = merge_scoped(
        [
            (channel, [Metric(name="active_user", definition="7d")]),
            (guild, [Metric(name="revenue", definition="net")]),
        ]
    )
    assert merged.lookup("active_user").definition == "7d"
    assert merged.lookup("revenue").definition == "net"


def test_resolver_effective_layer_guild_channel() -> None:
    store = SemanticStore()
    resolver = ScopeResolver(store)
    identity = Identity(user_id="u1", guild_id="g1", channel_id="c1")

    async def scenario() -> SemanticLayer:
        await resolver.define(
            Scope(ScopeLevel.GUILD, "g1"),
            Metric(name="active_user", definition="30d login"),
        )
        await resolver.define(
            Scope(ScopeLevel.GUILD, "g1"),
            Metric(name="revenue", definition="gross"),
        )
        # channel override of active_user only
        await resolver.define(
            Scope(ScopeLevel.CHANNEL, "c1"),
            Metric(name="active_user", definition="7d core action"),
        )
        return await resolver.effective_layer(identity)

    layer = asyncio.run(scenario())
    assert layer.lookup("active_user").definition == "7d core action"  # channel wins
    assert layer.lookup("revenue").definition == "gross"  # inherited from guild


def test_resolver_entries_at_no_inheritance() -> None:
    store = SemanticStore()
    resolver = ScopeResolver(store)

    async def scenario() -> list[SemanticEntry]:
        await resolver.define(
            Scope(ScopeLevel.GUILD, "g1"),
            Metric(name="revenue", definition="gross"),
        )
        # channel has nothing of its own
        return await resolver.entries_at(Scope(ScopeLevel.CHANNEL, "c1"))

    assert asyncio.run(scenario()) == []
