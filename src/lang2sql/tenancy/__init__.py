"""Tenancy — per-scope secrets and context assembly.

The :class:`ContextConcierge` is the one place concrete safety/adapter
classes get wired together into a :class:`~lang2sql.harness.context.HarnessContext`.
"""

from __future__ import annotations

from .concierge import ContextConcierge
from .encrypted_secrets import EncryptedSecrets

__all__ = ["ContextConcierge", "EncryptedSecrets"]
