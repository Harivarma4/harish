"""Container wires the LLM provider from configuration."""

from __future__ import annotations

from atlas_ai.adapters.config import Settings
from atlas_ai.adapters.llm.mock_llm import MockLLM
from atlas_ai.api.container import Container


def test_explicit_mock_provider() -> None:
    container = Container(Settings(adapter_mode="mock", llm_provider="mock"))
    assert isinstance(container.llm, MockLLM)
    assert container._model_version == container.llm.model_version
    assert container._llm_is_real is False


def test_anthropic_provider_degrades_to_mock_without_claude() -> None:
    # Selecting the anthropic provider routes to AnthropicLLM. Without the
    # optional `anthropic` package / credentials, the container degrades to the
    # deterministic mock (with a warning) instead of crashing.
    container = Container(Settings(adapter_mode="mock", llm_provider="anthropic"))
    assert isinstance(container.llm, MockLLM)
    assert container._llm_is_real is False
