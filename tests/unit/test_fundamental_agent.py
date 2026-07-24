"""Fundamental agent scoring behaviour."""

from __future__ import annotations

from atlas_ai.application.agents.base import AgentContext
from atlas_ai.application.agents.fundamental_agent import FundamentalAgent
from atlas_ai.domain.enums import AgentKind
from atlas_ai.domain.market import Instrument, Quote
from tests.conftest import make_candles, make_fundamentals


def _ctx(instrument: Instrument, **f: float) -> AgentContext:
    fundamentals = make_fundamentals(instrument, **f)
    quote = Quote(instrument, 100.0, 101.0, 99.0, 1_000_000)
    return AgentContext(instrument, quote, make_candles([100.0]), fundamentals, 100_000.0)


def test_high_quality_outscores_low_quality(instrument: Instrument) -> None:
    agent = FundamentalAgent()
    strong = agent.analyze(
        _ctx(instrument, roe_pct=30, roce_pct=35, debt_to_equity=0.1,
             net_margin_pct=20, earnings_growth_pct=25, pe=18)
    )
    weak = agent.analyze(
        _ctx(instrument, roe_pct=5, roce_pct=6, debt_to_equity=1.8,
             net_margin_pct=2, earnings_growth_pct=-4, pe=55)
    )
    assert strong.score.value > weak.score.value
    assert strong.agent is AgentKind.FUNDAMENTAL


def test_leverage_and_pledge_surface_as_risks(instrument: Instrument) -> None:
    agent = FundamentalAgent()
    report = agent.analyze(_ctx(instrument, debt_to_equity=1.5, promoter_pledge_pct=12, pe=45))
    joined = " ".join(report.risks).lower()
    assert "leverage" in joined
    assert "pledg" in joined
    assert "valuation" in joined
