"""Broker + LLM wiring in the composition root (offline, no credentials)."""

from __future__ import annotations

from atlas_ai.adapters.broker.mock_broker import MockBroker
from atlas_ai.adapters.config import Settings
from atlas_ai.adapters.llm.mock_llm import MockLLM
from atlas_ai.api.container import Container
from atlas_ai.domain.enums import AgentKind


def _real_no_creds() -> Container:
    # Real mode, but no Kite credentials -> broker must fall back to the mock.
    # All real feed adapters construct lazily (no network at build time).
    return Container(Settings(adapter_mode="real", llm_provider="mock"))


def test_real_mode_without_credentials_falls_back_to_mock_broker() -> None:
    container = _real_no_creds()
    assert isinstance(container.broker, MockBroker)
    assert container._broker_is_real is False


def test_status_flags_broker_as_non_real_without_credentials() -> None:
    status = _real_no_creds().orchestrator.status()
    portfolio = next(a for a in status.agents if a.kind is AgentKind.PORTFOLIO)
    assert "(real)" not in portfolio.data_basis
    assert any("Kite credentials" in n or "kite" in n.lower() for n in status.readiness_notes)


def test_default_llm_falls_back_to_mock_without_claude() -> None:
    # Default llm_provider is anthropic; without the package/credentials the
    # container degrades to the deterministic mock rather than crashing.
    container = Container(Settings(adapter_mode="real"))
    assert isinstance(container.llm, MockLLM)
    assert container._llm_is_real is False


def test_status_flags_debate_as_mock_without_claude() -> None:
    status = Container(Settings(adapter_mode="real")).orchestrator.status()
    debate = next(a for a in status.agents if a.kind is AgentKind.DEBATE)
    assert "(real)" not in debate.data_basis
    assert any(
        "anthropic" in n.lower() or "claude" in n.lower() for n in status.readiness_notes
    )
