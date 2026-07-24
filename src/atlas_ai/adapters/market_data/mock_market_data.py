"""Deterministic, offline mock market-data adapter (quotes + candles).

Candle history is a seeded geometric random walk, so the same symbol always
yields the same series (reproducible research). The *data* is synthetic; the
*analysis* run on it is real.
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np

from atlas_ai.adapters.sample_data import CANONICAL_DAYS, profile, seed_for
from atlas_ai.domain.market import Candle, Instrument, Quote


class MockMarketData:
    """Satisfies ``MarketDataPort`` with deterministic synthetic prices."""

    def __init__(self, *, today: date | None = None) -> None:
        self._today = today or date(2026, 1, 1)

    def get_candles(self, instrument: Instrument, *, days: int) -> list[Candle]:
        p = profile(instrument.symbol)
        rng = np.random.default_rng(seed_for(instrument.symbol) + 1)
        mu = p["drift"] / 252.0
        sigma = 0.015
        prices = [float(p["base_price"])]
        for _ in range(days):
            prices.append(max(prices[-1] * (1.0 + rng.normal(mu, sigma)), 1.0))
        prices = prices[1:]

        candles: list[Candle] = []
        start = self._today - timedelta(days=days)
        for i, close in enumerate(prices):
            intraday = abs(rng.normal(0.0, sigma)) * close
            open_ = close * (1.0 + rng.normal(0.0, sigma / 2))
            high = max(open_, close) + intraday
            low = max(min(open_, close) - intraday, 1.0)
            candles.append(
                Candle(
                    on=start + timedelta(days=i),
                    open=round(open_, 2),
                    high=round(high, 2),
                    low=round(low, 2),
                    close=round(close, 2),
                    volume=int(rng.integers(100_000, 5_000_000)),
                )
            )
        return candles

    def get_quote(self, instrument: Instrument) -> Quote:
        candles = self.get_candles(instrument, days=CANONICAL_DAYS)
        last = candles[-1]
        return Quote(
            instrument=instrument,
            last_price=last.close,
            day_high=last.high,
            day_low=last.low,
            volume=last.volume,
        )
