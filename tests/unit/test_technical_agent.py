"""Technical agent scoring behaviour."""

from __future__ import annotations

from atlas_ai.application.agents.base import AgentContext
from atlas_ai.application.agents.technical_agent import TechnicalAgent
from atlas_ai.domain.market import Instrument, Quote
from tests.conftest import make_candles, make_fundamentals


def _ctx(instrument: Instrument, closes: list[float]) -> AgentContext:
    candles = make_candles(closes)
    last = candles[-1].close
    quote = Quote(instrument, last, last * 1.01, last * 0.99, 1_000_000)
    return AgentContext(
        instrument, quote, candles, make_fundamentals(instrument), 100_000.0
    )


def test_uptrend_outscores_downtrend(instrument: Instrument) -> None:
    agent = TechnicalAgent()
    up = agent.analyze(_ctx(instrument, [100 + i for i in range(220)]))
    down = agent.analyze(_ctx(instrument, [320 - i for i in range(220)]))
    assert up.score.value > down.score.value


def test_handles_short_history_without_error(instrument: Instrument) -> None:
    agent = TechnicalAgent()
    report = agent.analyze(_ctx(instrument, [100.0, 101.0, 102.0]))
    assert 0.0 <= report.score.value <= 100.0
