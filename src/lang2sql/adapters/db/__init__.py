"""DB adapters — :class:`ExplorerPort` impls + the connection factory.

``build_explorer`` routes a connection string to the right adapter:
Cloudflare D1 over its HTTP API, everything else over generic SQLAlchemy.
"""

from __future__ import annotations

from .d1_explorer import D1Explorer
from .factory import build_explorer, explorer_from_env
from .postgres_explorer import PostgresExplorer
from .sqlalchemy_explorer import SqlAlchemyExplorer

__all__ = [
    "build_explorer",
    "explorer_from_env",
    "D1Explorer",
    "SqlAlchemyExplorer",
    "PostgresExplorer",
]
