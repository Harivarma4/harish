"""File-backed fundamentals provider.

Because Zerodha Kite Connect (and most broker/market-data feeds) do not expose
company fundamentals, this provider lets you supply your own researched dataset
as a JSON file. Each entry may be keyed by ``"EXCHANGE:SYMBOL"`` (e.g.
``"NSE:RELIANCE"``) or by bare ``"SYMBOL"``.

Example ``fundamentals.json``::

    {
      "NSE:RELIANCE": {
        "market_cap_cr": 1900000, "pe": 24.0, "pb": 2.3,
        "roe_pct": 9.0, "roce_pct": 11.0, "debt_to_equity": 0.42,
        "operating_margin_pct": 17.0, "net_margin_pct": 8.0,
        "revenue_growth_pct": 10.0, "earnings_growth_pct": 11.0,
        "dividend_yield_pct": 0.4, "promoter_holding_pct": 50.3,
        "promoter_pledge_pct": 0.0
      }
    }
"""

from __future__ import annotations

import json
from pathlib import Path

from atlas_ai.domain.market import Fundamentals, Instrument

_REQUIRED_FIELDS = (
    "market_cap_cr", "pe", "pb", "roe_pct", "roce_pct", "debt_to_equity",
    "operating_margin_pct", "net_margin_pct", "revenue_growth_pct",
    "earnings_growth_pct", "dividend_yield_pct", "promoter_holding_pct",
    "promoter_pledge_pct",
)


class FundamentalsNotFound(KeyError):
    """Raised when the dataset has no entry for the requested instrument."""


class FileFundamentalsProvider:
    """Satisfies ``FundamentalsPort`` by reading a user-supplied JSON dataset."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        if not self._path.is_file():
            raise FileNotFoundError(f"Fundamentals file not found: {self._path}")
        raw = json.loads(self._path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("Fundamentals file must contain a JSON object at the top level")
        self._data: dict[str, dict[str, float]] = {k.upper(): v for k, v in raw.items()}

    def get_fundamentals(self, instrument: Instrument) -> Fundamentals:
        entry = self._data.get(instrument.key.upper()) or self._data.get(
            instrument.symbol.upper()
        )
        if entry is None:
            raise FundamentalsNotFound(
                f"No fundamentals for {instrument.key} in {self._path}. "
                f"Add an entry keyed by '{instrument.key}' or '{instrument.symbol}'."
            )
        missing = [f for f in _REQUIRED_FIELDS if f not in entry]
        if missing:
            raise ValueError(
                f"Fundamentals for {instrument.key} missing fields: {', '.join(missing)}"
            )
        return Fundamentals(
            instrument=instrument,
            market_cap_cr=float(entry["market_cap_cr"]),
            pe=float(entry["pe"]),
            pb=float(entry["pb"]),
            roe_pct=float(entry["roe_pct"]),
            roce_pct=float(entry["roce_pct"]),
            debt_to_equity=float(entry["debt_to_equity"]),
            operating_margin_pct=float(entry["operating_margin_pct"]),
            net_margin_pct=float(entry["net_margin_pct"]),
            revenue_growth_pct=float(entry["revenue_growth_pct"]),
            earnings_growth_pct=float(entry["earnings_growth_pct"]),
            dividend_yield_pct=float(entry["dividend_yield_pct"]),
            promoter_holding_pct=float(entry["promoter_holding_pct"]),
            promoter_pledge_pct=float(entry["promoter_pledge_pct"]),
        )
