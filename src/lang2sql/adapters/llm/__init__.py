"""LLM adapters — :class:`LLMPort` impls."""

from __future__ import annotations

from .fake import FakeLLM
from .openai_ import OpenAILLM

__all__ = ["FakeLLM", "OpenAILLM"]
