"""Deterministic, offline mock fundamentals provider.

Illustrative values only (see ``adapters/sample_data``). Use ``file`` fundamentals
in real mode to supply your own researched data.
"""

from __future__ import annotations

from atlas_ai.adapters.sample_data import profile
from atlas_ai.domain.market import Fundamentals, Instrument


class MockFundamentals:
    """Satisfies ``FundamentalsPort`` with deterministic synthetic ratios."""

    def get_fundamentals(self, instrument: Instrument) -> Fundamentals:
        p = profile(instrument.symbol)
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
