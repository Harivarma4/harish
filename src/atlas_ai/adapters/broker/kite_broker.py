"""Real Zerodha Kite Connect broker adapter (read-only portfolio access).

Implements ``BrokerPort`` against the live Kite Connect API: equity holdings and
available margins. It needs a valid API key and a daily access token and outbound
access to Kite, so it runs where you deploy it, not in an offline sandbox. Order
placement is deliberately NOT implemented — this is read-only, portfolio-aware
research.

Design notes
------------
- The concrete ``kiteconnect`` client is *injected* (or lazily constructed from
  credentials) behind a minimal ``KiteBrokerClient`` Protocol, so the parsing and
  mapping here are fully unit-tested with a fake client, no network required.
- Holdings on non-equity exchanges (NFO/CDS/…) are skipped: this adapter models
  an equity book. ``t1_quantity`` (bought but not yet settled) is included so the
  position size matches what the investor actually owns.

References: Kite Connect v3 — ``holdings`` and ``margins`` endpoints.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol, runtime_checkable

from atlas_ai.application.ports.broker import Holding, Margins
from atlas_ai.domain.enums import Exchange
from atlas_ai.domain.market import Instrument

logger = logging.getLogger("atlas_ai.broker")

_EXCHANGES = {"NSE": Exchange.NSE, "BSE": Exchange.BSE}


@runtime_checkable
class KiteBrokerClient(Protocol):
    """The subset of ``kiteconnect.KiteConnect`` this adapter uses."""

    def holdings(self) -> list[dict[str, Any]]: ...

    def margins(self, segment: str | None = None) -> dict[str, Any]: ...


class KiteBrokerError(RuntimeError):
    """Raised for adapter-level failures talking to Kite."""


def _build_client(api_key: str, access_token: str) -> KiteBrokerClient:
    """Construct a real KiteConnect client. Import is lazy so the base package
    does not depend on ``kiteconnect`` unless real mode is actually used."""
    try:
        from kiteconnect import KiteConnect  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise KiteBrokerError(
            "The 'kiteconnect' package is required for the real broker. "
            "Install it with: pip install 'atlas-ai[kite]'"
        ) from exc
    client = KiteConnect(api_key=api_key)
    client.set_access_token(access_token)
    return client


class KiteBroker:
    """Live equity holdings and margins from Zerodha Kite Connect."""

    def __init__(
        self,
        *,
        api_key: str = "",
        access_token: str = "",
        client: KiteBrokerClient | None = None,
    ) -> None:
        if client is None:
            if not api_key or not access_token:
                raise KiteBrokerError(
                    "KiteBroker needs either an injected client or both "
                    "api_key and access_token."
                )
            client = _build_client(api_key, access_token)
        self._client = client

    # -- BrokerPort -------------------------------------------------------

    def get_holdings(self) -> list[Holding]:
        try:
            rows = self._client.holdings()
        except Exception as exc:  # noqa: BLE001 - surface SDK/network errors uniformly
            raise KiteBrokerError(f"Kite holdings failed: {exc}") from exc
        holdings: list[Holding] = []
        for row in rows:
            holding = self._to_holding(row)
            if holding is not None:
                holdings.append(holding)
        return holdings

    def get_margins(self) -> Margins:
        try:
            equity = self._client.margins("equity")
        except Exception as exc:  # noqa: BLE001 - surface SDK/network errors uniformly
            raise KiteBrokerError(f"Kite margins failed: {exc}") from exc
        available = equity.get("available") or {}
        cash = _to_float(available.get("live_balance", available.get("cash", 0.0)))
        net = _to_float(equity.get("net", cash))
        return Margins(net=net, available_cash=cash)

    # -- internals --------------------------------------------------------

    @staticmethod
    def _to_holding(row: dict[str, Any]) -> Holding | None:
        exchange = _EXCHANGES.get(str(row.get("exchange", "")).upper())
        symbol = str(row.get("tradingsymbol", "")).strip()
        if exchange is None or not symbol:
            return None  # non-equity or malformed row — not part of the equity book
        quantity = int(row.get("quantity") or 0) + int(row.get("t1_quantity") or 0)
        if quantity == 0:
            return None
        return Holding(
            instrument=Instrument(symbol, exchange),
            quantity=quantity,
            average_price=_to_float(row.get("average_price")),
            last_price=_to_float(row.get("last_price")),
        )


def _to_float(value: Any) -> float:
    if value is None:
        return 0.0
    return float(value)
