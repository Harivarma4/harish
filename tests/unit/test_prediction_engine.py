"""Prediction engine: reproducibility, ranges, and directionality."""

from __future__ import annotations

from atlas_ai.application.agents.base import AgentContext
from atlas_ai.application.prediction.engine import PredictionEngine
from atlas_ai.domain.analysis import AgentReport
from atlas_ai.domain.debate import DebateArgument, DebateOutcome
from atlas_ai.domain.enums import AgentKind
from atlas_ai.domain.market import Instrument, Quote
from atlas_ai.domain.value_objects import Score
from tests.conftest import make_candles, make_fundamentals


def _ctx(instrument: Instrument) -> AgentContext:
    candles = make_candles([100 + (i % 5) for i in range(120)])
    quote = Quote(instrument, candles[-1].close, 105.0, 99.0, 1_000_000)
    return AgentContext(instrument, quote, candles, make_fundamentals(instrument), 100_000.0)


def _reports(score: float) -> list[AgentReport]:
    return [
        AgentReport(AgentKind.FUNDAMENTAL, Score(score), (), "f"),
        AgentReport(AgentKind.TECHNICAL, Score(score), (), "t"),
        AgentReport(AgentKind.RISK, Score(score), (), "r"),
    ]


def _debate(leaning: float) -> DebateOutcome:
    bull = DebateArgument("BULL", "bull", ())
    bear = DebateArgument("BEAR", "bear", ())
    return DebateOutcome(bull, bear, "verdict", leaning)


def test_reproducible_with_fixed_seed(instrument: Instrument) -> None:
    ctx = _ctx(instrument)
    engine = PredictionEngine(simulations=2000, seed=7)
    a = engine.forecast(ctx, _reports(70), _debate(0.4), horizon_days=126)
    b = engine.forecast(ctx, _reports(70), _debate(0.4), horizon_days=126)
    assert a == b


def test_probability_in_unit_interval(instrument: Instrument) -> None:
    outlook = PredictionEngine(simulations=2000).forecast(
        _ctx(instrument), _reports(60), _debate(0.2), horizon_days=126
    )
    assert 0.0 <= outlook.probability_favourable <= 1.0
    assert outlook.cagr_p05.value <= outlook.cagr_p95.value


def test_bullish_scores_beat_bearish(instrument: Instrument) -> None:
    ctx = _ctx(instrument)
    engine = PredictionEngine(simulations=4000, seed=1)
    bull = engine.forecast(ctx, _reports(85), _debate(0.7), horizon_days=252)
    bear = engine.forecast(ctx, _reports(20), _debate(-0.7), horizon_days=252)
    assert bull.probability_favourable > bear.probability_favourable
    assert bull.expected_cagr.value > bear.expected_cagr.value
