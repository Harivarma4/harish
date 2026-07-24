"""Fundamentals port — company financials for the fundamental agent.

Separate from ``MarketDataPort`` because the data comes from a different class of
source (filings, a fundamentals vendor, or a user-supplied dataset) than a
market/price feed like Zerodha Kite Connect.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from atlas_ai.domain.market import Fundamentals, Instrument


@runtime_checkable
class FundamentalsPort(Protocol):
    """Read access to company fundamentals for an instrument."""

    def get_fundamentals(self, instrument: Instrument) -> Fundamentals: ...
