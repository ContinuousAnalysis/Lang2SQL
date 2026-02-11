# lang2sql/core/context.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional
from collections.abc import MutableMapping


@dataclass(init=False)
class RunContext:
    """
    A minimal state carrier for define-by-run pipelines.

    Internal storage is generic:
    - inputs: user inputs (e.g., query)
    - artifacts: intermediate artifacts (e.g., schema candidates, prompt context)
    - outputs: final outputs (e.g., sql, validation)
    - error: structured error information (optional)
    - metadata: logs/traces/history (optional)

    Public UX can be domain-friendly via alias properties:
    - .query, .schema, .sql, .validation, etc.
    """

    inputs: dict[str, Any] = field(default_factory=dict)
    artifacts: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    error: Optional[dict[str, Any]] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __init__(self, query: Optional[str] = None, **kwargs: Any) -> None:
        # Keep storage generic and always initialized.
        self.inputs = {}
        self.artifacts = {}
        self.outputs = {}
        self.error = None
        self.metadata = {}

        if query is not None:
            self.inputs["query"] = query

        # Allow lightweight initialization: RunContext(foo=..., bar=...)
        # Store unknown fields in metadata to avoid schema lock-in.
        if kwargs:
            self.metadata.update(kwargs)

    # -------------------------
    # Domain-friendly aliases
    # -------------------------

    @property
    def query(self) -> str:
        """Return the user question/query."""
        v = self.inputs.get("query", "")
        if v is None:
            return ""
        if isinstance(v, str):
            return v
        # Be forgiving: keep pipeline running, but avoid crashing on accidental types.
        return str(v)

    @query.setter
    def query(self, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError(f"RunContext.query must be str, got {type(value).__name__}")
        self.inputs["query"] = value

    @property
    def schema(self) -> MutableMapping[str, Any]:
        """
        Return the schema artifact mapping.

        Typical keys (convention):
        - catalog: full schema catalog (list/provider)
        - selected: top-k table candidates
        - context: final context text used for prompting
        """
        v = self.artifacts.get("schema")
        if v is None:
            v = {}
            self.artifacts["schema"] = v
            return v

        if isinstance(v, MutableMapping):
            return v

        # If someone wrote a non-mapping value, replace it to keep conventions stable.
        v = {}
        self.artifacts["schema"] = v
        return v

    @property
    def sql(self) -> str:
        """Return the final SQL string."""
        v = self.outputs.get("sql", "")
        if v is None:
            return ""
        if isinstance(v, str):
            return v
        return str(v)

    @sql.setter
    def sql(self, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError(f"RunContext.sql must be str, got {type(value).__name__}")
        self.outputs["sql"] = value

    @property
    def validation(self) -> Any:
        """Return validation result object, if present."""
        return self.outputs.get("validation")

    @validation.setter
    def validation(self, value: Any) -> None:
        self.outputs["validation"] = value

    # Optional convenience aliases (recommended for discoverability)

    @property
    def schema_catalog(self) -> Any:
        """Alias for schema['catalog']."""
        return self.schema.get("catalog")

    @schema_catalog.setter
    def schema_catalog(self, value: Any) -> None:
        self.schema["catalog"] = value

    @property
    def schema_selected(self) -> Any:
        """Alias for schema['selected']."""
        return self.schema.get("selected")

    @schema_selected.setter
    def schema_selected(self, value: Any) -> None:
        self.schema["selected"] = value

    @property
    def schema_context(self) -> str:
        """Alias for schema['context']."""
        v = self.schema.get("context", "")
        if v is None:
            return ""
        if isinstance(v, str):
            return v
        return str(v)

    @schema_context.setter
    def schema_context(self, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError(f"RunContext.schema_context must be str, got {type(value).__name__}")
        self.schema["context"] = value

    # -------------------------
    # Small utilities
    # -------------------------

    def push_meta(self, key: str, value: Any) -> None:
        """
        Append a value into metadata[key] list.

        Example:
            run.push_meta("sql_drafts", sql)
            run.push_meta("events", event)
        """
        arr = self.metadata.setdefault(key, [])
        if not isinstance(arr, list):
            raise TypeError(f"metadata['{key}'] exists but is not a list")
        arr.append(value)

    def get_meta_list(self, key: str) -> list[Any]:
        """Return metadata[key] as a list (empty list if missing)."""
        v = self.metadata.get(key)
        if v is None:
            return []
        if isinstance(v, list):
            return v
        return [v]