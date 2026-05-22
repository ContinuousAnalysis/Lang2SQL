"""Tenancy — scope resolution, per-scope secrets, and context assembly.

The :class:`ContextConcierge` is the one place concrete semantic/safety/adapter
classes get wired together into a :class:`~lang2sql.harness.context.HarnessContext`.
"""

from __future__ import annotations

from .concierge import ContextConcierge
from .encrypted_secrets import EncryptedSecrets
from .scope_resolver import ScopeResolver

__all__ = ["ContextConcierge", "EncryptedSecrets", "ScopeResolver"]
