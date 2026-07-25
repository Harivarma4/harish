"""Memory agent — institutional-memory prior from past recommendations."""

from __future__ import annotations

from dataclasses import dataclass

from atlas_ai.application.agents.base import AgentContext
from atlas_ai.application.agents.memory_agent import MemoryAgent
from atlas_ai.domain.enums import Action, AgentKind, Exchange, SignalStrength
from atlas_ai.domain.market import Instrument, Quote
from atlas_ai.domain.value_objects import Confidence
from tests.conftest import make_candles, make_fundamentals


@dataclass
class _Rec:
    """Minimal stand-in exposing only what the memory agent reads."""

    instrument: Instrument
    action: Action
    confidence: Confidence


class _FakeRepo:
    def __init__(self, recs: list[_Rec]) -> None:
        # list_recent returns most-recent first, mirroring the real repository.
        self._recs = recs

    def save(self, recommendation: object) -> None:  # pragma: no cover - unused
        raise NotImplementedError

    def get(self, recommendation_id: str) -> object | None:  # pragma: no cover - unused
        return None

    def list_recent(self, *, limit: int = 50) -> list[_Rec]:
        return list(self._recs[:limit])


def _ctx(symbol: str = "RELIANCE") -> AgentContext:
    instrument = Instrument(symbol, Exchange.NSE)
    candles = make_candles([100.0 + (i % 4) for i in range(30)])
    quote = Quote(instrument, 100.0, 101.0, 99.0, 1_000_000)
    return AgentContext(instrument, quote, candles, make_fundamentals(instrument), 100_000.0)


def _rec(symbol: str, action: Action, conf: float = 0.6) -> _Rec:
    return _Rec(Instrument(symbol, Exchange.NSE), action, Confidence(conf))


def _stance(signals: tuple) -> SignalStrength:
    return next(s for s in signals if s.name == "PriorStance").strength


def test_no_prior_coverage_is_neutral() -> None:
    report = MemoryAgent(_FakeRepo([])).analyze(_ctx())
    assert report.agent is AgentKind.MEMORY
    assert report.score.value == 50.0
    assert _stance(report.signals) is SignalStrength.NEUTRAL


def test_consistent_bullish_history_leans_bullish() -> None:
    recs = [_rec("RELIANCE", Action.BUY) for _ in range(4)]
    report = MemoryAgent(_FakeRepo(recs)).analyze(_ctx())
    assert _stance(report.signals) in {
        SignalStrength.BULLISH, SignalStrength.STRONG_BULLISH
    }


def test_consistent_bearish_history_leans_bearish() -> None:
    recs = [_rec("RELIANCE", Action.SELL) for _ in range(4)]
    report = MemoryAgent(_FakeRepo(recs)).analyze(_ctx())
    assert _stance(report.signals) in {
        SignalStrength.BEARISH, SignalStrength.STRONG_BEARISH
    }


def test_filters_by_instrument() -> None:
    # Only the matching-instrument history should count.
    recs = [_rec("INFY", Action.SELL), _rec("INFY", Action.SELL), _rec("RELIANCE", Action.BUY)]
    report = MemoryAgent(_FakeRepo(recs)).analyze(_ctx("RELIANCE"))
    assert "1 prior look" in report.rationale
    assert _stance(report.signals) in {
        SignalStrength.BULLISH, SignalStrength.STRONG_BULLISH
    }


def test_recency_weighting_favours_latest() -> None:
    # Latest call is bullish, older ones bearish; recency weighting tilts up.
    recs = [_rec("RELIANCE", Action.BUY), _rec("RELIANCE", Action.SELL),
            _rec("RELIANCE", Action.SELL)]
    report = MemoryAgent(_FakeRepo(recs)).analyze(_ctx("RELIANCE"))
    stance_value = next(s for s in report.signals if s.name == "PriorStance").value
    plain_mean = (1.0 - 1.0 - 1.0) / 3.0
    assert stance_value is not None and stance_value > plain_mean


def test_single_look_consistency_is_neutral_only() -> None:
    report = MemoryAgent(_FakeRepo([_rec("RELIANCE", Action.BUY)])).analyze(_ctx())
    consistency = next(s for s in report.signals if s.name == "PriorConsistency")
    assert consistency.strength is SignalStrength.NEUTRAL
