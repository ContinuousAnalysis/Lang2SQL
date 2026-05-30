"""Persistence tests — SqliteSemanticStore durability + Fernet secrets (★④ §4.1).

Two guarantees under test: (1) semantic definitions and secrets survive a fresh
store instance pointed at the same sqlite file, and (2) secrets are stored as
real Fernet ciphertext, not recoverable without the key.
"""

from __future__ import annotations

import asyncio
import os

import pytest
from cryptography.fernet import Fernet, InvalidToken

from lang2sql.adapters.storage.sqlite_semantic import SqliteSemanticStore
from lang2sql.adapters.storage.sqlite_store import SqliteStore
from lang2sql.core.identity import Identity, Scope, ScopeLevel
from lang2sql.semantic.types import Metric, SemanticKind
from lang2sql.tenancy.encrypted_secrets import EncryptedSecrets
from lang2sql.tenancy.scope_resolver import ScopeResolver


def test_semantic_store_add_entries_at_round_trip() -> None:
    store = SqliteSemanticStore()
    scope = Scope(ScopeLevel.CHANNEL, "c1")
    store.add(scope, Metric("revenue", "sum of order totals", created_by="u1"))

    entries = store.entries_at(scope)
    assert len(entries) == 1
    assert entries[0].name == "revenue"
    assert entries[0].kind is SemanticKind.METRIC
    assert entries[0].definition == "sum of order totals"
    assert entries[0].created_by == "u1"
    # created_at is preserved, not regenerated.
    assert entries[0].created_at != ""

    # Re-adding the same name at the same scope replaces it.
    store.add(scope, Metric("revenue", "net revenue"))
    entries = store.entries_at(scope)
    assert len(entries) == 1
    assert entries[0].definition == "net revenue"

    # A different scope is isolated.
    assert store.entries_at(Scope(ScopeLevel.CHANNEL, "other")) == []


def test_semantic_store_survives_new_instance_on_same_file(tmp_path) -> None:
    db = str(tmp_path / "semantic.db")
    scope = Scope(ScopeLevel.GUILD, "g1")

    writer = SqliteSemanticStore(db)
    writer.add(scope, Metric("aov", "avg order value", source_id="doc-7"))
    created_at = writer.entries_at(scope)[0].created_at
    writer.close()

    # A fresh instance on the same path sees the persisted definition.
    reader = SqliteSemanticStore(db)
    entries = reader.entries_at(scope)
    assert len(entries) == 1
    assert entries[0].name == "aov"
    assert entries[0].definition == "avg order value"
    assert entries[0].source_id == "doc-7"
    assert entries[0].created_at == created_at
    reader.close()


def test_scope_resolver_effective_layer_over_sqlite_store() -> None:
    store = SqliteSemanticStore()
    # Narrow (channel) overrides wide (guild) for the same name.
    store.add(Scope(ScopeLevel.GUILD, "g1"), Metric("revenue", "guild-wide def"))
    store.add(Scope(ScopeLevel.CHANNEL, "c1"), Metric("revenue", "channel def"))
    store.add(Scope(ScopeLevel.GUILD, "g1"), Metric("churn", "guild churn"))

    resolver = ScopeResolver(store)
    identity = Identity(user_id="u1", guild_id="g1", channel_id="c1")
    layer = asyncio.run(resolver.effective_layer(identity))

    by_name = {e.name: e.definition for e in layer.entries}
    assert by_name["revenue"] == "channel def"  # most specific wins
    assert by_name["churn"] == "guild churn"  # inherited from guild


def test_encrypted_secrets_round_trip_and_ciphertext(tmp_path) -> None:
    # Explicit key so the test is independent of env / generated state.
    key = Fernet.generate_key()
    store = SqliteStore()
    secrets = EncryptedSecrets(store, key=key)

    assert asyncio.run(secrets.get("guild:1", "dsn")) is None
    asyncio.run(secrets.set("guild:1", "dsn", "postgresql://u:p@host/db"))
    assert asyncio.run(secrets.get("guild:1", "dsn")) == "postgresql://u:p@host/db"

    # What actually lands in kv is a Fernet token, never the plaintext.
    blob = store.kv_get("guild:1", "dsn")
    assert blob is not None
    assert "postgresql" not in blob
    assert blob != "postgresql://u:p@host/db"
    # It decrypts only with the right key.
    assert Fernet(key).decrypt(blob.encode("ascii")).decode() == "postgresql://u:p@host/db"

    asyncio.run(secrets.delete("guild:1", "dsn"))
    assert asyncio.run(secrets.get("guild:1", "dsn")) is None


def test_encrypted_secrets_wrong_key_fails() -> None:
    store = SqliteStore()
    asyncio.run(EncryptedSecrets(store, key=Fernet.generate_key()).set("s", "k", "v"))

    # A different key cannot decrypt the stored token.
    attacker = EncryptedSecrets(store, key=Fernet.generate_key())
    with pytest.raises(InvalidToken):
        asyncio.run(attacker.get("s", "k"))


def test_encrypted_secrets_survive_new_instance_via_persisted_key(tmp_path) -> None:
    db = str(tmp_path / "secrets.db")
    # No env key -> a key is generated and persisted in the kv table.
    saved = os.environ.pop("LANG2SQL_SECRET_KEY", None)
    try:
        store = SqliteStore(db)
        asyncio.run(EncryptedSecrets(store).set("guild:1", "dsn", "postgresql://x"))
        store.close()

        # A fresh store + secrets on the same file reuses the persisted key.
        reopened = SqliteStore(db)
        secrets = EncryptedSecrets(reopened)
        assert asyncio.run(secrets.get("guild:1", "dsn")) == "postgresql://x"
        reopened.close()
    finally:
        if saved is not None:
            os.environ["LANG2SQL_SECRET_KEY"] = saved


def test_concierge_path_persists_definitions_and_secrets(tmp_path) -> None:
    from lang2sql.adapters.llm.fake import FakeLLM
    from lang2sql.tenancy.concierge import ContextConcierge

    db = str(tmp_path / "concierge.db")
    saved = os.environ.pop("LANG2SQL_SECRET_KEY", None)
    try:
        c1 = ContextConcierge(path=db, llm=FakeLLM())
        scope = Scope(ScopeLevel.CHANNEL, "c1")
        asyncio.run(c1.scope_resolver.define(scope, Metric("revenue", "sum totals")))
        asyncio.run(c1.secrets.set("guild:1", "dsn", "postgresql://secret"))
        c1.store.close()
        c1.scope_resolver.store.close()

        c2 = ContextConcierge(path=db, llm=FakeLLM())
        assert [e.name for e in asyncio.run(c2.scope_resolver.entries_at(scope))] == [
            "revenue"
        ]
        assert asyncio.run(c2.secrets.get("guild:1", "dsn")) == "postgresql://secret"
    finally:
        if saved is not None:
            os.environ["LANG2SQL_SECRET_KEY"] = saved
