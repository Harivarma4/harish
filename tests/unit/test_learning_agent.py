"""Learning agent — instrument-specific calibration from a self-backtest."""

from __future__ import annotations

from atlas_ai.application.agents.base import AgentContext
from atlas_ai.application.agents.learning_agent import LearningAgent
from atlas_ai.domain.enums import AgentKind, Exchange, SignalStrength
from atlas_ai.domain.market import Instrument, Quote
from tests.conftest import make_candles, make_fundamentals

_INSTRUMENT = Instrument("RELIANCE", Exchange.NSE)


def _ctx(closes: list[float]) -> AgentContext:
    candles = make_candles(closes)
    last = candles[-1].close
    quote = Quote(_INSTRUMENT, last, last * 1.01, last * 0.99, 1_000_000)
    return AgentContext(_INSTRUMENT, quote, candles, make_fundamentals(_INSTRUMENT), 100_000.0)


def _named(signals: tuple, name: str) -> SignalStrength:
    return next(s for s in signals if s.name == name).strength


def test_insufficient_history_is_neutral() -> None:
    report = LearningAgent().analyze(_ctx([100.0, 101.0, 102.0, 103.0]))
    assert report.agent is AgentKind.LEARNING
    assert report.score.value == 50.0
    assert _named(report.signals, "BacktestHitRate") is SignalStrength.NEUTRAL


def test_persistent_uptrend_has_positive_edge() -> None:
    # A steady uptrend: the long-above-SMA rule pays off almost every time.
    report = LearningAgent().analyze(_ctx([100.0 + i for i in range(120)]))
    assert _named(report.signals, "BacktestHitRate") in {
        SignalStrength.BULLISH, SignalStrength.STRONG_BULLISH
    }
    live = next(s for s in report.signals if s.name == "LiveRuleSignal")
    assert live.strength in {SignalStrength.BULLISH, SignalStrength.STRONG_BULLISH}


def test_rule_flat_when_currently_below_sma() -> None:
    # Rise (rule engages, building history) then a sharp reversal so the latest
    # close is below its SMA: the live rule is flat even though trades exist.
    closes = [100.0 + i for i in range(100)] + [199.0 - 4.0 * i for i in range(1, 40)]
    report = LearningAgent().analyze(_ctx(closes))
    live = next(s for s in report.signals if s.name == "LiveRuleSignal")
    assert live.strength is SignalStrength.NEUTRAL


def test_all_signals_present_and_scoreable() -> None:
    report = LearningAgent().analyze(_ctx([100.0 + (i % 7) for i in range(150)]))
    names = {s.name for s in report.signals}
    assert names == {"BacktestHitRate", "BacktestSharpe", "LiveRuleSignal"}
    assert 0.0 <= report.score.value <= 100.0


def test_backtest_is_deterministic() -> None:
    closes = [100.0 + (i % 5) - (i % 3) for i in range(140)]
    a = LearningAgent().analyze(_ctx(closes))
    b = LearningAgent().analyze(_ctx(closes))
    assert a.score.value == b.score.value
