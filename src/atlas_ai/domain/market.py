"""Market-data domain entities: instruments, quotes, candles, fundamentals."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from atlas_ai.domain.enums import Exchange


@dataclass(frozen=True, slots=True)
class Instrument:
    """A tradable listed instrument."""

    symbol: str
    exchange: Exchange
    name: str | None = None

    @property
    def key(self) -> str:
        return f"{self.exchange.value}:{self.symbol}"


@dataclass(frozen=True, slots=True)
class Quote:
    """A last-traded snapshot."""

    instrument: Instrument
    last_price: float
    day_high: float
    day_low: float
    volume: int


@dataclass(frozen=True, slots=True)
class Candle:
    """A single OHLCV bar."""

    on: date
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass(frozen=True, slots=True)
class Fundamentals:
    """Point-in-time company fundamentals used by the fundamental agent.

    Values are expressed in their natural units (ratios as ratios, margins as
    percentages, growth as percentages). Absolute rupee figures are in crores.
    """

    instrument: Instrument
    market_cap_cr: float
    pe: float
    pb: float
    roe_pct: float
    roce_pct: float
    debt_to_equity: float
    operating_margin_pct: float
    net_margin_pct: float
    revenue_growth_pct: float
    earnings_growth_pct: float
    dividend_yield_pct: float
    promoter_holding_pct: float
    promoter_pledge_pct: float

    @property
    def peg(self) -> float | None:
        """Price/earnings-to-growth. ``None`` when growth is non-positive."""
        if self.earnings_growth_pct <= 0:
            return None
        return round(self.pe / self.earnings_growth_pct, 3)
