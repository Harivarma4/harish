"""Mock Zerodha-style broker adapter (read-only portfolio access).

Stands in for Zerodha Kite Connect. Order placement is intentionally not
implemented in this foundation build; only holdings and margins are exposed.
"""

from __future__ import annotations

from atlas_ai.application.ports.broker import Holding, Margins
from atlas_ai.domain.enums import Exchange
from atlas_ai.domain.market import Instrument


class MockBroker:
    """Satisfies ``BrokerPort`` with a small static portfolio."""

    def __init__(self) -> None:
        self._holdings = [
            Holding(
                instrument=Instrument("TCS", Exchange.NSE, "Tata Consultancy Services"),
                quantity=10,
                average_price=3600.0,
                last_price=3850.0,
            ),
            Holding(
                instrument=Instrument("HDFCBANK", Exchange.NSE, "HDFC Bank"),
                quantity=25,
                average_price=1500.0,
                last_price=1650.0,
            ),
        ]

    def get_holdings(self) -> list[Holding]:
        return list(self._holdings)

    def get_margins(self) -> Margins:
        return Margins(net=250_000.0, available_cash=180_000.0)
