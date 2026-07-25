"""Weekly-trend use case computes a correct factual summary."""

from __future__ import annotations

from datetime import date, timedelta

from atlas_ai.application.use_cases.get_weekly_trend import (
    GetWeeklyTrend,
    GetWeeklyTrendCommand,
)
from atlas_ai.domain.enums import Exchange
from atlas_ai.domain.market import Candle, Instrument


class FakeMarketData:
    def __init__(self, closes: list[float]) -> None:
        self._closes = closes
        self.requested_days: int | None = None

    def get_candles(self, instrument: Instrument, *, days: int) -> list[Candle]:
        self.requested_days = days
        start = date(2026, 7, 17)
        return [
            Candle(on=start + timedelta(days=i), open=c, high=c + 5, low=c - 5,
                   close=c, volume=1_000_000)
            for i, c in enumerate(self._closes[:days])
        ]

    def get_quote(self, instrument: Instrument):  # pragma: no cover - unused here
        raise NotImplementedError


def _run(closes: list[float], sessions: int = 5):
    md = FakeMarketData(closes)
    uc = GetWeeklyTrend(market_data=md)
    return md, uc.execute(GetWeeklyTrendCommand(symbol="reliance", sessions=sessions))


def test_uptrend_summary() -> None:
    md, t = _run([2900.0, 2928.0, 2905.0, 2941.0, 2963.0])
    assert md.requested_days == 5
    assert t.instrument == Instrument("RELIANCE", Exchange.NSE)
    assert t.first_close == 2900.0 and t.last_close == 2963.0
    assert t.change_pct == round((2963 - 2900) / 2900 * 100, 2)
    assert t.direction == "UP"
    assert t.week_high == 2968.0 and t.week_low == 2895.0   # +/-5 on extremes
    assert t.sma == round(sum([2900, 2928, 2905, 2941, 2963]) / 5, 2)
    assert len(t.sessions) == 5
    assert t.disclaimer


def test_downtrend_direction() -> None:
    _, t = _run([3000.0, 2980.0, 2950.0, 2900.0, 2850.0])
    assert t.direction == "DOWN"
    assert t.change_pct < 0


def test_flat_direction_within_band() -> None:
    _, t = _run([1000.0, 1001.0, 999.5, 1000.5, 1002.0])  # ~+0.2%
    assert t.direction == "FLAT"


def test_custom_session_count() -> None:
    md, t = _run([10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0], sessions=10)
    assert md.requested_days == 10
    assert len(t.sessions) == 10
