"""Orchestration layer — system status and role coordination."""

from __future__ import annotations

from atlas_ai.application.orchestration.orchestrator import Orchestrator
from atlas_ai.application.orchestration.roster import AGENT_PROFILES
from atlas_ai.application.prediction.engine import AGENT_WEIGHTS
from atlas_ai.domain.enums import AgentKind


def _orch(*, notes: tuple[str, ...] = ()) -> Orchestrator:
    data_basis = {
        AgentKind.FUNDAMENTAL: "Yahoo Finance fundamentals (real)",
        AgentKind.TECHNICAL: "Yahoo Finance prices (real)",
        AgentKind.MACRO: "Yahoo + official figures (real)",
        AgentKind.NEWS: "Google News RSS (real)",
        AgentKind.OPTIONS: "NSE option chain (real)",
        AgentKind.PORTFOLIO: "Mock broker holdings (real adapter pending)",
    }
    return Orchestrator(
        app_name="Project Atlas AI",
        version="0.1.0",
        adapter_mode="real",
        pipeline_version="research-pipeline-v1",
        data_basis=data_basis,
        readiness_notes=notes,
    )


def test_status_covers_every_profiled_agent() -> None:
    status = _orch().status()
    assert status.agent_count == len(AGENT_PROFILES)
    kinds = {a.kind for a in status.agents}
    assert kinds == set(AGENT_PROFILES)


def test_scored_agents_carry_weights_synthesis_do_not() -> None:
    status = _orch().status()
    by_kind = {a.kind: a for a in status.agents}
    assert by_kind[AgentKind.FUNDAMENTAL].weight == AGENT_WEIGHTS[AgentKind.FUNDAMENTAL]
    # Debate/evidence are synthesis stages, not weighted specialists.
    assert by_kind[AgentKind.DEBATE].weight is None
    assert by_kind[AgentKind.EVIDENCE].weight is None


def test_real_data_agents_are_counted() -> None:
    status = _orch().status()
    # The five feed-backed agents marked "(real)" above.
    assert status.live_on_real_data == 5


def test_readiness_reflects_notes() -> None:
    clean = _orch().status()
    assert clean.cto_readiness == "All agents live on real data."
    degraded = _orch(notes=("Broker uses the mock adapter.",)).status()
    assert "1 surface" in degraded.cto_readiness
    assert degraded.readiness_notes == ("Broker uses the mock adapter.",)


def test_every_agent_has_role_and_responsibilities() -> None:
    status = _orch().status()
    for a in status.agents:
        assert a.role
        assert a.responsibilities
        assert a.status == "operational"


def test_ceo_mandate_states_research_not_advice() -> None:
    mandate = _orch().status().ceo_mandate.lower()
    assert "research" in mandate
    assert "no deterministic" in mandate
