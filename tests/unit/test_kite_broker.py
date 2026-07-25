"""Real Zerodha Kite broker adapter parsing (offline, via a fake client)."""

from __future__ import annotations

from typing import Any

import pytest

from atlas_ai.adapters.broker.kite_broker import KiteBroker, KiteBrokerError
from atlas_ai.domain.enums import Exchange


class _FakeKite:
    def __init__(self, holdings: list[dict[str, Any]], margins: dict[str, Any]) -> None:
        self._holdings = holdings
        self._margins = margins
        self.margin_segment: str | None = None

    def holdings(self) -> list[dict[str, Any]]:
        return self._holdings

    def margins(self, segment: str | None = None) -> dict[str, Any]:
        self.margin_segment = segment
        return self._margins


def _holding(symbol: str, exchange: str, qty: int, avg: float, ltp: float,
             t1: int = 0) -> dict[str, Any]:
    return {
        "tradingsymbol": symbol, "exchange": exchange, "quantity": qty,
        "t1_quantity": t1, "average_price": avg, "last_price": ltp,
    }


_MARGINS = {"net": 250000.0, "available": {"live_balance": 180000.0, "cash": 175000.0}}


def test_maps_equity_holdings() -> None:
    kite = _FakeKite(
        [_holding("INFY", "NSE", 10, 1400.0, 1500.0),
         _holding("TCS", "BSE", 5, 3600.0, 3850.0)],
        _MARGINS,
    )
    holdings = KiteBroker(client=kite).get_holdings()
    assert [h.instrument.symbol for h in holdings] == ["INFY", "TCS"]
    assert holdings[0].instrument.exchange is Exchange.NSE
    assert holdings[1].instrument.exchange is Exchange.BSE
    assert holdings[0].pnl == (1500.0 - 1400.0) * 10


def test_includes_t1_quantity() -> None:
    kite = _FakeKite([_holding("RELIANCE", "NSE", 8, 2800.0, 2900.0, t1=2)], _MARGINS)
    holdings = KiteBroker(client=kite).get_holdings()
    assert holdings[0].quantity == 10  # 8 settled + 2 unsettled


def test_skips_non_equity_and_zero_qty() -> None:
    kite = _FakeKite(
        [_holding("NIFTY24JAN", "NFO", 50, 100.0, 120.0),  # derivatives — skipped
         _holding("IDEA", "NSE", 0, 10.0, 11.0),           # zero qty — skipped
         _holding("HDFCBANK", "NSE", 3, 1500.0, 1650.0)],
        _MARGINS,
    )
    holdings = KiteBroker(client=kite).get_holdings()
    assert [h.instrument.symbol for h in holdings] == ["HDFCBANK"]


def test_margins_prefers_live_balance() -> None:
    kite = _FakeKite([], _MARGINS)
    margins = KiteBroker(client=kite).get_margins()
    assert margins.net == 250000.0
    assert margins.available_cash == 180000.0
    assert kite.margin_segment == "equity"


def test_margins_falls_back_to_cash() -> None:
    kite = _FakeKite([], {"net": 90000.0, "available": {"cash": 90000.0}})
    margins = KiteBroker(client=kite).get_margins()
    assert margins.available_cash == 90000.0


def test_requires_client_or_credentials() -> None:
    with pytest.raises(KiteBrokerError):
        KiteBroker()


def test_holdings_error_is_wrapped() -> None:
    class _Boom:
        def holdings(self) -> list[dict[str, Any]]:
            raise RuntimeError("network down")

        def margins(self, segment: str | None = None) -> dict[str, Any]:
            return {}

    with pytest.raises(KiteBrokerError):
        KiteBroker(client=_Boom()).get_holdings()
