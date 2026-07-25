"""Use case: read the last week's price trend for an instrument.

This is a *factual* read of recent historical prices — not a recommendation and
not a prediction. It computes the week's change, direction, range, and a simple
moving average from the last N daily sessions supplied by the ``MarketDataPort``
(so it reflects whatever source is configured: Yahoo public feed, Kite, or mock).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from atlas_ai.application.ports.market_data import MarketDataPort
from atlas_ai.domain.enums import Exchange
from atlas_ai.domain.market import Instrument

TREND_DISCLAIMER = (
    "Historical price data for research only — not investment advice. Past "
    "performance does not indicate future results."
)
# Change within +/- this % is treated as flat rather than up/down.
_FLAT_BAND_PCT = 0.5


@dataclass(frozen=True, slots=True)
class SessionClose:
    on: date
    close: float


@dataclass(frozen=True, slots=True)
class TrendSummary:
    """A factual summary of an instrument's recent price action."""

    instrument: Instrument
    sessions: tuple[SessionClose, ...]
    first_close: float
    last_close: float
    change_pct: float
    direction: str  # "UP" | "DOWN" | "FLAT"
    week_high: float
    week_low: float
    sma: float
    as_of: date
    disclaimer: str = TREND_DISCLAIMER


@dataclass(frozen=True, slots=True)
class GetWeeklyTrendCommand:
    symbol: str
    exchange: Exchange = Exchange.NSE
    sessions: int = 5  # ~1 trading week


class GetWeeklyTrend:
    """Computes a recent-trend summary from the market-data port."""

    def __init__(self, *, market_data: MarketDataPort) -> None:
        self._market_data = market_data

    def execute(self, command: GetWeeklyTrendCommand) -> TrendSummary:
        instrument = Instrument(symbol=command.symbol.upper(), exchange=command.exchange)
        span = max(1, command.sessions)
        candles = self._market_data.get_candles(instrument, days=span)
        if not candles:
            raise ValueError(f"No price data available for {instrument.key}")

        closes = [c.close for c in candles]
        first, last = closes[0], closes[-1]
        change_pct = ((last - first) / first * 100.0) if first else 0.0
        if change_pct > _FLAT_BAND_PCT:
            direction = "UP"
        elif change_pct < -_FLAT_BAND_PCT:
            direction = "DOWN"
        else:
            direction = "FLAT"

        return TrendSummary(
            instrument=instrument,
            sessions=tuple(SessionClose(c.on, c.close) for c in candles),
            first_close=first,
            last_close=last,
            change_pct=round(change_pct, 2),
            direction=direction,
            week_high=round(max(c.high for c in candles), 2),
            week_low=round(min(c.low for c in candles), 2),
            sma=round(sum(closes) / len(closes), 2),
            as_of=candles[-1].on,
        )
