"""Shared synthetic profiles backing the mock adapters.

Illustrative, NOT live values. Used by both the mock market-data adapter (for a
seeded price walk) and the mock fundamentals provider (for ratios). Kept in one
place so the two mocks stay consistent for a given symbol.
"""

from __future__ import annotations

import hashlib

import numpy as np

# Canonical history length; the mock "current" quote is the last bar of this
# series so the quote and the analyzed candles agree on the latest price.
CANONICAL_DAYS = 260

# Curated profiles for a handful of well-known large-caps (illustrative only).
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


def seed_for(symbol: str) -> int:
    digest = hashlib.sha256(symbol.encode()).hexdigest()
    return int(digest[:8], 16)


def profile(symbol: str) -> dict[str, float]:
    """Return a stable synthetic profile for a symbol (curated or hash-derived)."""
    if symbol in _CURATED:
        return _CURATED[symbol]
    rng = np.random.default_rng(seed_for(symbol))
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
