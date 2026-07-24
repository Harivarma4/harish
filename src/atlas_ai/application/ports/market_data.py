"""Market-data port — supplies quotes and candles (prices).

Fundamentals are deliberately *not* here: a trading/market-data feed such as
Zerodha Kite Connect provides prices and candles but not company fundamentals.
Fundamentals live behind their own port (``FundamentalsPort``).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from atlas_ai.domain.market import Candle, Instrument, Quote


@runtime_checkable
class MarketDataPort(Protocol):
    """Read access to price data for an instrument."""

    def get_quote(self, instrument: Instrument) -> Quote: ...

    def get_candles(self, instrument: Instrument, *, days: int) -> list[Candle]: ...
