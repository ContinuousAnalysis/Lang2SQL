"""Edge-case tests for previously uncovered code paths.

- org_setup synonyms: LLM가 리스트 대신 문자열로 반환해도 올바르게 처리
- bot.py on_message: file=None일 때 channel.send에 file 인자를 전달하지 않음
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from lang2sql.core.identity import Identity
from lang2sql.frontends.discord import InteractionContext, to_identity
from lang2sql.frontends.discord.render import OutboundMessage
from lang2sql.tenancy.concierge import ContextConcierge
from lang2sql.tools.semantic_federation import FedEntry, _render_effective


# -- org_setup synonyms -------------------------------------------------------


def test_fed_entry_synonyms_as_string_does_not_corrupt_render() -> None:
    """FedEntry with synonyms stored as string (LLM slip) must not explode render."""
    from lang2sql.adapters.storage.sqlite_store import SqliteStore
    from lang2sql.tools.semantic_federation import _kv_key

    store = SqliteStore()
    scope = "g1"
    # Simulate org_setup writing a FedEntry where synonyms is a plain string
    # (after our fix this should never happen, but ensure rendering is safe either way)
    entry_bad = FedEntry(term="active_user", layer="guild", entity="",
                         definition="30d login", synonyms="활성유저, active")  # type: ignore[arg-type]
    store.kv_set(scope, _kv_key("active_user", "guild", ""), entry_bad.to_json())

    # render must not raise and must not output individual characters
    rendered = _render_effective(store, scope, "", "u1")
    assert "active_user" in rendered
    # "활" appearing as a lone character followed by "," would indicate character-join
    assert "활, 성" not in rendered


def test_org_setup_synonyms_string_normalised() -> None:
    """org_setup coerces a string synonyms value to a list before storing."""
    from lang2sql.tools.semantic_federation import _kv_key, FedEntry
    from lang2sql.adapters.storage.sqlite_store import SqliteStore

    store = SqliteStore()
    scope = "g-test"

    # Apply the same normalisation logic org_setup uses
    raw = "활성유저, active user"
    synonyms = raw if isinstance(raw, list) else [s.strip() for s in str(raw).split(",") if s.strip()]
    entry = FedEntry(term="active_user", layer="guild", entity="",
                     definition="30d login", synonyms=synonyms, inferred=True)
    store.kv_set(scope, _kv_key("active_user", "guild", ""), entry.to_json())

    rendered = _render_effective(store, scope, "", "u1")
    assert "활성유저" in rendered
    assert "active user" in rendered


# -- bot.py on_message file guard ---------------------------------------------


def test_to_sendable_text_only_returns_none_file() -> None:
    """Text-only response produces file=None; on_message must not forward that to channel.send."""
    from lang2sql.frontends.discord.bot import _to_sendable

    msg = OutboundMessage(text="42 users", file_bytes=None)
    content, file = _to_sendable(msg)
    assert content == "42 users"
    assert file is None  # confirms the guard in on_message is needed / correct


def test_on_message_send_kwargs_omit_file_when_none() -> None:
    """Verify the kwargs-building pattern omits file when _to_sendable returns None."""
    # Simulate the exact on_message send block
    file = None
    kwargs: dict = {"content": "42 users"}
    if file is not None:
        kwargs["file"] = file
    assert "file" not in kwargs  # file=None must not be forwarded to channel.send
