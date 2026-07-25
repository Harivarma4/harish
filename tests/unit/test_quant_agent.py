"""Quant/factor agent scoring behaviour."""

from __future__ import annotations

from atlas_ai.application.agents.base import AgentContext
from atlas_ai.application.agents.quant_agent import QuantAgent
from atlas_ai.domain.enums import AgentKind, Exchange, SignalStrength
from atlas_ai.domain.market import Instrument, Quote
from tests.conftest import make_candles, make_fundamentals


def _ctx(closes: list[float], **f: float) -> AgentContext:
    instrument = Instrument("RELIANCE", Exchange.NSE)
    candles = make_candles(closes)
    last = candles[-1].close
    quote = Quote(instrument, last, last * 1.01, last * 0.99, 1_000_000)
    return AgentContext(
        instrument, quote, candles, make_fundamentals(instrument, **f), 100_000.0
    )


def test_strong_factors_outscore_weak() -> None:
    agent = QuantAgent()
    # Steady uptrend + high quality + cheap valuation.
    strong = agent.analyze(
        _ctx([100 + i * 0.8 for i in range(220)],
             roe_pct=30, debt_to_equity=0.1, net_margin_pct=20, pe=12, pb=2)
    )
    # Downtrend + low quality + expensive.
    weak = agent.analyze(
        _ctx([300 - i * 0.8 for i in range(220)],
             roe_pct=5, debt_to_equity=1.8, net_margin_pct=2, pe=55, pb=11)
    )
    assert strong.score.value > weak.score.value
    assert strong.agent is AgentKind.QUANT


def test_all_factor_signals_present() -> None:
    report = QuantAgent().analyze(_ctx([100 + (i % 5) for i in range(120)]))
    names = {s.name for s in report.signals}
    assert names == {"Momentum", "LowVol", "MeanReversion", "Quality", "Value"}
    assert 0.0 <= report.score.value <= 100.0


def test_positive_momentum_is_bullish() -> None:
    report = QuantAgent().analyze(_ctx([100 + i for i in range(200)]))
    momentum = next(s for s in report.signals if s.name == "Momentum")
    assert momentum.strength in {SignalStrength.BULLISH, SignalStrength.STRONG_BULLISH}
    assert momentum.value is not None and momentum.value > 0


def test_short_history_is_handled() -> None:
    report = QuantAgent().analyze(_ctx([100.0, 101.0, 102.0]))
    assert 0.0 <= report.score.value <= 100.0
