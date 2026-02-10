import pytest

from lang2sql.core.exceptions import (
    IntegrationMissingError,
    ComponentError,
    Lang2SQLError,
)

def test_integration_missing_error_message_includes_extra_hint():
    err = IntegrationMissingError("faiss", extra="faiss")
    msg = str(err)
    assert "Missing optional integration: faiss" in msg
    assert "pip install 'lang2sql[faiss]'" in msg

def test_integration_missing_error_message_includes_hint_when_provided():
    err = IntegrationMissingError("openai", extra="openai", hint="Needed for LLM calls")
    msg = str(err)
    assert "Missing optional integration: openai" in msg
    assert "pip install 'lang2sql[openai]'" in msg
    assert "Needed for LLM calls" in msg

def test_component_error_wraps_component_name_and_message():
    err = ComponentError("KeywordTableRetriever", "component failed")
    msg = str(err)
    assert msg.startswith("[KeywordTableRetriever]")
    assert "component failed" in msg

def test_exceptions_are_subclasses_of_base_error():
    assert issubclass(IntegrationMissingError, Lang2SQLError)
    assert issubclass(ComponentError, Lang2SQLError)

def test_component_error_can_chain_cause():
    root = ValueError("boom")
    err = ComponentError("X", "failed", cause=root)
    assert err.cause is root