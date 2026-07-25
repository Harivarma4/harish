"""End-to-end pipeline through the use case with mock adapters."""

from __future__ import annotations

import pytest

from atlas_ai.api.container import Container
from atlas_ai.application.use_cases.generate_recommendation import (
    GenerateRecommendationCommand,
)
from atlas_ai.domain.enums import Action, Exchange, TimeHorizon


@pytest.fixture
def container() -> Container:
    return Container()


def test_generate_recommendation_is_complete(container: Container) -> None:
    use_case = container.generate_recommendation()
    rec = use_case.execute(
        GenerateRecommendationCommand(symbol="RELIANCE", exchange=Exchange.NSE, capital=100_000)
    )

    # Guardrails present.
    assert rec.disclaimer
    assert rec.assumptions and rec.known_risks and rec.evidence
    assert 0.0 <= rec.confidence.value <= 1.0
    assert isinstance(rec.action, Action)

    # Full analytical payload present.
    kinds = {r.agent for r in rec.agent_reports}
    assert len(kinds) == 4  # fundamental, technical, macro, risk
    assert 0.0 <= rec.outlook.probability_favourable <= 1.0
    assert rec.outlook.cagr_p05.value <= rec.outlook.cagr_p95.value
    assert rec.risk.stop_loss < rec.risk.entry_price < rec.risk.target_price
    assert rec.debate.bull.thesis and rec.debate.bear.thesis and rec.debate.verdict

    # Persisted + audited.
    assert container.repository.get(rec.id) is not None
    audit = container.audit.for_recommendation(rec.id)  # type: ignore[attr-defined]
    assert len(audit) == 1
    assert audit[0].model_version == rec.governance.model_version


def test_reproducible_across_runs() -> None:
    def run() -> float:
        c = Container()
        rec = c.generate_recommendation().execute(
            GenerateRecommendationCommand(symbol="INFY", time_horizon=TimeHorizon.LONG_TERM)
        )
        return rec.outlook.probability_favourable

    assert run() == run()
