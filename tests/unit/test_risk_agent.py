"""Risk agent: sizing, stops, reward:risk, VaR."""

from __future__ import annotations

from atlas_ai.application.agents.base import AgentContext
from atlas_ai.application.agents.risk_agent import RiskAgent, RiskPolicy
from atlas_ai.domain.enums import AgentKind
from atlas_ai.domain.market import Instrument, Quote
from tests.conftest import make_candles, make_fundamentals


def _ctx(instrument: Instrument, capital: float = 100_000.0) -> AgentContext:
    closes = [100 + (i % 7) for i in range(60)]
    candles = make_candles([float(c) for c in closes])
    last = candles[-1].close
    quote = Quote(instrument, last, last * 1.02, last * 0.98, 1_000_000)
    return AgentContext(instrument, quote, candles, make_fundamentals(instrument), capital)


def test_reward_to_risk_matches_policy(instrument: Instrument) -> None:
    agent = RiskAgent(RiskPolicy(reward_to_risk=2.0))
    assessment, report = agent.assess(_ctx(instrument))
    assert assessment.reward_to_risk == 2.0
    assert report.agent is AgentKind.RISK


def test_stop_below_entry_and_target_above(instrument: Instrument) -> None:
    assessment, _ = RiskAgent().assess(_ctx(instrument))
    assert assessment.stop_loss < assessment.entry_price < assessment.target_price


def test_position_never_exceeds_capital(instrument: Instrument) -> None:
    assessment, _ = RiskAgent().assess(_ctx(instrument, capital=5_000.0))
    assert assessment.position_value.amount <= 5_000.0


def test_var_is_non_negative(instrument: Instrument) -> None:
    assessment, _ = RiskAgent().assess(_ctx(instrument))
    assert assessment.value_at_risk_pct.value >= 0.0
