"""Container wires the LLM provider from configuration."""

from __future__ import annotations

import pytest

from atlas_ai.adapters.config import Settings
from atlas_ai.adapters.llm.anthropic_llm import AnthropicError
from atlas_ai.adapters.llm.mock_llm import MockLLM
from atlas_ai.api.container import Container


def test_default_provider_is_mock() -> None:
    container = Container(Settings(llm_provider="mock"))
    assert isinstance(container.llm, MockLLM)
    assert container._model_version == container.llm.model_version


def test_anthropic_provider_builds_claude_adapter() -> None:
    # Selecting the anthropic provider routes to AnthropicLLM. Without the
    # optional `anthropic` package installed, constructing the real client
    # fails with AnthropicError — proving the wiring reaches the adapter.
    with pytest.raises(AnthropicError):
        Container(Settings(llm_provider="anthropic"))
