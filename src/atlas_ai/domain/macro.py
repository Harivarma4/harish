"""Macroeconomic indicators — the top-down backdrop for equity research."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class MacroIndicators:
    """A point-in-time snapshot of India-relevant macro variables.

    Market-wide (not instrument-specific): the macro agent uses these as a
    top-down overlay on bottom-up fundamental/technical analysis.
    """

    repo_rate_pct: float          # RBI policy repo rate
    cpi_inflation_pct: float      # headline CPI, year-over-year
    gdp_growth_pct: float         # real GDP growth, year-over-year
    india_10y_yield_pct: float    # 10-year government bond yield
    usd_inr: float                # rupee per US dollar
    crude_oil_usd: float          # Brent crude, USD/bbl
    fii_flow_cr: float            # recent net FII equity flow, crores (+buy/-sell)
    global_equity_trend_pct: float  # recent trend in global equities, %
    as_of: date
