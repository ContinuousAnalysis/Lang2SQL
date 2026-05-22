"""EncryptedSecrets — per-scope credential storage over a :class:`SqliteStore` kv.

V1 obfuscation only: each value is XOR'd against a static key and base64-encoded
before it lands in the kv table. This is *not* real encryption — it keeps
plaintext DSNs/API keys out of casual ``sqlite3`` browsing, nothing more. Real
KMS/Fernet-backed encryption is deferred to v1.5 (the :class:`SecretsPort`
boundary lets that drop in without touching callers).
"""

from __future__ import annotations

import base64

from ..adapters.storage.sqlite_store import SqliteStore

# Static obfuscation key. Not a secret and not security — see module docstring.
_XOR_KEY = b"lang2sql-v1-obfuscation-key"


def _xor(data: bytes) -> bytes:
    return bytes(b ^ _XOR_KEY[i % len(_XOR_KEY)] for i, b in enumerate(data))


def _obfuscate(value: str) -> str:
    return base64.b64encode(_xor(value.encode("utf-8"))).decode("ascii")


def _deobfuscate(blob: str) -> str:
    return _xor(base64.b64decode(blob)).decode("utf-8")


class EncryptedSecrets:
    """Implements :class:`SecretsPort` on top of a kv-capable store."""

    def __init__(self, store: SqliteStore) -> None:
        self._store = store

    async def get(self, scope: str, key: str) -> str | None:
        blob = self._store.kv_get(scope, key)
        return _deobfuscate(blob) if blob is not None else None

    async def set(self, scope: str, key: str, value: str) -> None:
        self._store.kv_set(scope, key, _obfuscate(value))

    async def delete(self, scope: str, key: str) -> None:
        self._store.kv_delete(scope, key)
