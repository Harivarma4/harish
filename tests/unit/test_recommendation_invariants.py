"""The Recommendation aggregate must refuse to be built without its guardrails."""

from __future__ import annotations

import pytest

from atlas_ai.domain.debate import DebateArgument, DebateOutcome
from atlas_ai.domain.enums import Action, Conviction, Exchange, TimeHorizon
from atlas_ai.domain.evidence import Evidence, Source
from atlas_ai.domain.forecast import ProbabilisticOutlook
from atlas_ai.domain.governance import GovernanceMetadata
from atlas_ai.domain.market import Instrument
from atlas_ai.domain.recommendation import Recommendation
from atlas_ai.domain.risk import RiskAssessment
from atlas_ai.domain.value_objects import Confidence, Money, Percent

INSTRUMENT = Instrument("RELIANCE", Exchange.NSE)


def _outlook() -> ProbabilisticOutlook:
    return ProbabilisticOutlook(
        probability_favourable=0.6,
        expected_cagr=Percent(12.0),
        cagr_p05=Percent(-8.0),
        cagr_p95=Percent(30.0),
        confidence=Confidence(0.6),
        simulations=1000,
    )


def _risk() -> RiskAssessment:
    return RiskAssessment(
        entry_price=100.0, stop_loss=90.0, target_price=120.0, quantity=10,
        capital_at_risk=Money(100.0), position_value=Money(1000.0),
        reward_to_risk=2.0, value_at_risk_pct=Percent(3.0), var_confidence=0.95,
    )


def _debate() -> DebateOutcome:
    return DebateOutcome(
        DebateArgument("BULL", "bull", ()), DebateArgument("BEAR", "bear", ()),
        "verdict", 0.2,
    )


def _evidence() -> tuple[Evidence, ...]:
    return (Evidence("ROE strong", Source("engine", 0.8), 0.5),)


def _governance() -> GovernanceMetadata:
    return GovernanceMetadata("m", "p", "pipe", "reasoning")


def _kwargs(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = dict(
        instrument=INSTRUMENT, action=Action.BUY, conviction=Conviction.MODERATE,
        confidence=Confidence(0.6), time_horizon=TimeHorizon.MEDIUM_TERM,
        executive_summary="Buy with moderate conviction.", outlook=_outlook(),
        risk=_risk(), debate=_debate(), agent_reports=(),
        catalysts=("growth",), assumptions=("data is accurate",),
        known_risks=("leverage",), unknown_risks=("macro",),
        counter_arguments=("valuation",), evidence=_evidence(),
        governance=_governance(),
    )
    base.update(overrides)
    return base


def test_valid_recommendation_builds() -> None:
    rec = Recommendation(**_kwargs())  # type: ignore[arg-type]
    assert rec.disclaimer
    assert rec.action is Action.BUY


@pytest.mark.parametrize(
    "field", ["assumptions", "known_risks", "evidence"]
)
def test_missing_guardrail_raises(field: str) -> None:
    with pytest.raises(ValueError):
        Recommendation(**_kwargs(**{field: ()}))  # type: ignore[arg-type]


def test_empty_summary_raises() -> None:
    with pytest.raises(ValueError):
        Recommendation(**_kwargs(executive_summary="   "))  # type: ignore[arg-type]


def test_evidence_partitions_into_support_and_counter() -> None:
    evidence = (
        Evidence("bull", Source("e", 0.8), 0.5),
        Evidence("bear", Source("e", 0.8), -0.5),
    )
    rec = Recommendation(**_kwargs(evidence=evidence))  # type: ignore[arg-type]
    assert len(rec.supporting_evidence) == 1
    assert len(rec.counter_evidence) == 1
