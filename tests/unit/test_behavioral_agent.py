"""Behavioral-finance agent — contrarian psychology from price + volume."""

from __future__ import annotations

from atlas_ai.application.agents.base import AgentContext
from atlas_ai.application.agents.behavioral_agent import BehavioralAgent
from atlas_ai.domain.enums import AgentKind, Exchange, SignalStrength
from atlas_ai.domain.market import Candle, Instrument, Quote
from tests.conftest import make_candles, make_fundamentals


def _ctx(candles: list[Candle]) -> AgentContext:
    instrument = Instrument("RELIANCE", Exchange.NSE)
    last = candles[-1].close
    quote = Quote(instrument, last, last * 1.01, last * 0.99, 1_000_000)
    return AgentContext(
        instrument, quote, candles, make_fundamentals(instrument), 100_000.0
    )


def _candles(closes: list[float], volumes: list[float] | None = None) -> list[Candle]:
    base = make_candles(closes)
    if volumes is None:
        return base
    return [
        Candle(on=c.on, open=c.open, high=c.high, low=c.low, close=c.close, volume=v)
        for c, v in zip(base, volumes, strict=True)
    ]


def test_report_shape_and_kind() -> None:
    report = BehavioralAgent().analyze(_ctx(make_candles([100 + (i % 4) for i in range(120)])))
    names = {s.name for s in report.signals}
    assert names == {"FearGreed", "VolRegime", "VolumeHerding"}
    assert report.agent is AgentKind.BEHAVIORAL
    assert 0.0 <= report.score.value <= 100.0
    assert report.assumptions and report.risks


def test_euphoric_extension_is_contrarian_caution() -> None:
    # A steep, extended rally reads as greed -> bearish (contrarian) fear/greed.
    report = BehavioralAgent().analyze(_ctx(make_candles([100 + i * 1.5 for i in range(120)])))
    fg = next(s for s in report.signals if s.name == "FearGreed")
    assert fg.strength in {SignalStrength.BEARISH, SignalStrength.STRONG_BEARISH}


def test_deep_capitulation_is_contrarian_opportunity() -> None:
    # A sharp sell-off reads as fear -> bullish (contrarian) fear/greed.
    report = BehavioralAgent().analyze(_ctx(make_candles([300 - i * 1.5 for i in range(120)])))
    fg = next(s for s in report.signals if s.name == "FearGreed")
    assert fg.strength in {SignalStrength.BULLISH, SignalStrength.STRONG_BULLISH}


def test_volume_surge_into_rally_is_herding() -> None:
    closes = [100.0 + i * 0.05 for i in range(35)] + [
        100.0 + 34 * 0.05 + i for i in range(1, 6)
    ]
    volumes = [1_000_000.0] * 35 + [5_000_000.0] * 5
    report = BehavioralAgent().analyze(_ctx(_candles(closes, volumes)))
    herding = next(s for s in report.signals if s.name == "VolumeHerding")
    assert herding.strength is SignalStrength.BEARISH


def test_volume_surge_into_selloff_is_capitulation() -> None:
    closes = [100.0 - i * 0.05 for i in range(35)] + [
        100.0 - 34 * 0.05 - i for i in range(1, 6)
    ]
    volumes = [1_000_000.0] * 35 + [5_000_000.0] * 5
    report = BehavioralAgent().analyze(_ctx(_candles(closes, volumes)))
    herding = next(s for s in report.signals if s.name == "VolumeHerding")
    assert herding.strength is SignalStrength.BULLISH


def test_short_history_is_handled() -> None:
    report = BehavioralAgent().analyze(_ctx(make_candles([100.0, 101.0, 102.0])))
    assert 0.0 <= report.score.value <= 100.0
    herding = next(s for s in report.signals if s.name == "VolumeHerding")
    assert herding.strength is SignalStrength.NEUTRAL
