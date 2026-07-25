"""Deterministic, offline mock macro provider.

Illustrative India macro values, NOT a live feed. A real adapter (RBI / public
data / vendor) implementing the same ``MacroPort`` can slot in later.
"""

from __future__ import annotations

from datetime import date

from atlas_ai.domain.macro import MacroIndicators


class MockMacro:
    """Satisfies ``MacroPort`` with a fixed, plausible macro snapshot."""

    def __init__(self, *, snapshot: MacroIndicators | None = None) -> None:
        self._snapshot = snapshot or MacroIndicators(
            repo_rate_pct=6.5,
            cpi_inflation_pct=5.1,
            gdp_growth_pct=6.8,
            india_10y_yield_pct=7.0,
            usd_inr=84.5,
            crude_oil_usd=82.0,
            fii_flow_cr=-1500.0,
            global_equity_trend_pct=1.2,
            as_of=date(2026, 1, 1),
        )

    def get_snapshot(self) -> MacroIndicators:
        return self._snapshot
