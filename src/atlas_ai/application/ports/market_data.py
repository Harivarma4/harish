"""Market-data port — supplies quotes, candles, and fundamentals."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from atlas_ai.domain.market import Candle, Fundamentals, Instrument, Quote


@runtime_checkable
class MarketDataPort(Protocol):
    """Read access to market and company data for an instrument."""

    def get_quote(self, instrument: Instrument) -> Quote: ...

    def get_candles(self, instrument: Instrument, *, days: int) -> list[Candle]: ...

    def get_fundamentals(self, instrument: Instrument) -> Fundamentals: ...
