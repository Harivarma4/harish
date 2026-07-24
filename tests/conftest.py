"""Shared test fixtures and factory helpers."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from atlas_ai.domain.enums import Exchange
from atlas_ai.domain.market import Candle, Fundamentals, Instrument


@pytest.fixture
def instrument() -> Instrument:
    return Instrument("RELIANCE", Exchange.NSE, "Reliance Industries")


def make_candles(closes: list[float]) -> list[Candle]:
    """Build a candle series from a list of closes with simple OHLC wrapping."""
    start = date(2025, 1, 1)
    candles: list[Candle] = []
    prev = closes[0]
    for i, close in enumerate(closes):
        high = max(prev, close) * 1.01
        low = min(prev, close) * 0.99
        candles.append(
            Candle(on=start + timedelta(days=i), open=prev, high=high, low=low,
                   close=close, volume=1_000_000)
        )
        prev = close
    return candles


def make_fundamentals(instrument: Instrument, **overrides: float) -> Fundamentals:
    base = dict(
        market_cap_cr=100_000.0, pe=20.0, pb=3.0, roe_pct=18.0, roce_pct=20.0,
        debt_to_equity=0.4, operating_margin_pct=18.0, net_margin_pct=12.0,
        revenue_growth_pct=14.0, earnings_growth_pct=16.0, dividend_yield_pct=1.0,
        promoter_holding_pct=50.0, promoter_pledge_pct=0.0,
    )
    base.update(overrides)
    return Fundamentals(instrument=instrument, **base)  # type: ignore[arg-type]
