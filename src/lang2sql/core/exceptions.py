# lang2sql/core/exceptions.py
from __future__ import annotations

class Lang2SQLError(Exception):
    """Base error for lang2sql."""


class IntegrationMissingError(Lang2SQLError):
    def __init__(self, integration: str, extra: str | None = None, hint: str | None = None):
        self.integration = integration
        self.extra = extra
        self.hint = hint

        msg = f"Missing optional integration: {integration}."
        if extra:
            msg += f" Install with: pip install 'lang2sql[{extra}]'"
        if hint:
            msg += f" ({hint})"
        super().__init__(msg)


class ComponentError(Lang2SQLError):
    def __init__(self, component: str, message: str, *, cause: Exception | None = None):
        self.component = component
        self.cause = cause
        super().__init__(f"[{component}] {message}")


class ValidationError(Lang2SQLError):
    pass