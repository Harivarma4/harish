"""Deterministic, offline mock market-data adapter.

Fundamentals for a few well-known Indian large-caps are curated; any other symbol
gets deterministic values derived from the symbol name. Candle history is a
seeded geometric random walk, so the same symbol always yields the same series
(reproducible research). The *data* is synthetic; the *analysis* run on it is
real.
"""

from __future__ import annotations

import hashlib
from datetime import date, timedelta

import numpy as np

from atlas_ai.domain.market import Candle, Fundamentals, Instrument, Quote

# Canonical history length; the "current" quote is the last bar of this series so
# the quote and the analyzed candles agree on the latest price.
_CANONICAL_DAYS = 260

# Curated fundamentals for a handful of symbols (illustrative, not live values).
_CURATED: dict[str, dict[str, float]] = {
    "RELIANCE": dict(
        market_cap_cr=1_900_000, pe=24.0, pb=2.3, roe_pct=9.0, roce_pct=11.0,
        debt_to_equity=0.42, operating_margin_pct=17.0, net_margin_pct=8.0,
        revenue_growth_pct=10.0, earnings_growth_pct=11.0, dividend_yield_pct=0.4,
        promoter_holding_pct=50.3, promoter_pledge_pct=0.0, base_price=2900.0, drift=0.05,
    ),
    "TCS": dict(
        market_cap_cr=1_400_000, pe=29.0, pb=13.0, roe_pct=47.0, roce_pct=58.0,
        debt_to_equity=0.09, operating_margin_pct=24.0, net_margin_pct=19.0,
        revenue_growth_pct=7.0, earnings_growth_pct=9.0, dividend_yield_pct=1.5,
        promoter_holding_pct=72.3, promoter_pledge_pct=0.0, base_price=3850.0, drift=0.04,
    ),
    "INFY": dict(
        market_cap_cr=650_000, pe=25.0, pb=8.0, roe_pct=31.0, roce_pct=40.0,
        debt_to_equity=0.10, operating_margin_pct=21.0, net_margin_pct=17.0,
        revenue_growth_pct=6.0, earnings_growth_pct=8.0, dividend_yield_pct=2.1,
        promoter_holding_pct=14.6, promoter_pledge_pct=0.0, base_price=1550.0, drift=0.03,
    ),
    "HDFCBANK": dict(
        market_cap_cr=1_250_000, pe=19.0, pb=2.7, roe_pct=17.0, roce_pct=15.0,
        debt_to_equity=0.85, operating_margin_pct=28.0, net_margin_pct=22.0,
        revenue_growth_pct=15.0, earnings_growth_pct=18.0, dividend_yield_pct=1.1,
        promoter_holding_pct=0.0, promoter_pledge_pct=0.0, base_price=1650.0, drift=0.06,
    ),
}


def _seed_for(symbol: str) -> int:
    digest = hashlib.sha256(symbol.encode()).hexdigest()
    return int(digest[:8], 16)


def _profile(symbol: str) -> dict[str, float]:
    if symbol in _CURATED:
        return _CURATED[symbol]
    # Derive a stable, plausible profile from the symbol hash.
    rng = np.random.default_rng(_seed_for(symbol))
    return dict(
        market_cap_cr=float(rng.integers(10_000, 500_000)),
        pe=float(round(rng.uniform(12, 45), 1)),
        pb=float(round(rng.uniform(1.0, 9.0), 1)),
        roe_pct=float(round(rng.uniform(6, 35), 1)),
        roce_pct=float(round(rng.uniform(7, 40), 1)),
        debt_to_equity=float(round(rng.uniform(0.05, 1.6), 2)),
        operating_margin_pct=float(round(rng.uniform(8, 30), 1)),
        net_margin_pct=float(round(rng.uniform(3, 22), 1)),
        revenue_growth_pct=float(round(rng.uniform(-2, 25), 1)),
        earnings_growth_pct=float(round(rng.uniform(-5, 30), 1)),
        dividend_yield_pct=float(round(rng.uniform(0.0, 3.0), 1)),
        promoter_holding_pct=float(round(rng.uniform(0, 75), 1)),
        promoter_pledge_pct=float(round(max(0.0, rng.uniform(-10, 20)), 1)),
        base_price=float(round(rng.uniform(100, 4000), 1)),
        drift=float(round(rng.uniform(-0.05, 0.08), 3)),
    )


class MockMarketData:
    """Satisfies ``MarketDataPort`` with deterministic synthetic data."""

    def __init__(self, *, today: date | None = None) -> None:
        self._today = today or date(2026, 1, 1)

    def get_fundamentals(self, instrument: Instrument) -> Fundamentals:
        p = _profile(instrument.symbol)
        return Fundamentals(
            instrument=instrument,
            market_cap_cr=p["market_cap_cr"],
            pe=p["pe"],
            pb=p["pb"],
            roe_pct=p["roe_pct"],
            roce_pct=p["roce_pct"],
            debt_to_equity=p["debt_to_equity"],
            operating_margin_pct=p["operating_margin_pct"],
            net_margin_pct=p["net_margin_pct"],
            revenue_growth_pct=p["revenue_growth_pct"],
            earnings_growth_pct=p["earnings_growth_pct"],
            dividend_yield_pct=p["dividend_yield_pct"],
            promoter_holding_pct=p["promoter_holding_pct"],
            promoter_pledge_pct=p["promoter_pledge_pct"],
        )

    def get_candles(self, instrument: Instrument, *, days: int) -> list[Candle]:
        p = _profile(instrument.symbol)
        rng = np.random.default_rng(_seed_for(instrument.symbol) + 1)
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
        candles = self.get_candles(instrument, days=_CANONICAL_DAYS)
        last = candles[-1]
        return Quote(
            instrument=instrument,
            last_price=last.close,
            day_high=last.high,
            day_low=last.low,
            volume=last.volume,
        )
