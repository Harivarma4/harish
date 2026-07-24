"""Real Zerodha Kite Connect market-data adapter (quotes + candles).

Implements ``MarketDataPort`` against the live Kite Connect API. It needs a valid
API key and a daily access token, and outbound network access to Kite — so it
runs where you deploy it, not in an offline sandbox.

Design notes
------------
- The concrete ``kiteconnect`` client is *injected* (or lazily constructed from
  credentials), and is described by a minimal ``KiteClient`` Protocol. That makes
  the parsing/mapping logic here fully unit-testable with a fake client, no
  network required.
- Kite's ``historical_data`` needs a numeric ``instrument_token``; we obtain it
  from the ``quote`` response and cache it per instrument.
- Kite does NOT provide fundamentals — those come from ``FundamentalsPort``.

References: Kite Connect v3 — ``quote`` and ``historical_data`` endpoints.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Protocol, runtime_checkable

from atlas_ai.domain.market import Candle, Instrument, Quote

# Kite caps a single historical_data call (daily interval) at ~2000 candles;
# stay well under that.
_MAX_DAYS = 1800


@runtime_checkable
class KiteClient(Protocol):
    """The subset of ``kiteconnect.KiteConnect`` this adapter uses."""

    def quote(self, instruments: list[str]) -> dict[str, Any]: ...

    def historical_data(
        self,
        instrument_token: int,
        from_date: datetime | date | str,
        to_date: datetime | date | str,
        interval: str,
        continuous: bool = False,
        oi: bool = False,
    ) -> list[dict[str, Any]]: ...


class KiteError(RuntimeError):
    """Raised for adapter-level failures talking to Kite."""


def _build_client(api_key: str, access_token: str) -> KiteClient:
    """Construct a real KiteConnect client. Import is lazy so the base package
    does not depend on ``kiteconnect`` unless real mode is actually used."""
    try:
        from kiteconnect import KiteConnect  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise KiteError(
            "The 'kiteconnect' package is required for real market data. "
            "Install it with: pip install 'atlas-ai[kite]'"
        ) from exc
    client = KiteConnect(api_key=api_key)
    client.set_access_token(access_token)
    return client


class KiteMarketData:
    """Live quotes and daily candles from Zerodha Kite Connect."""

    def __init__(
        self,
        *,
        api_key: str = "",
        access_token: str = "",
        client: KiteClient | None = None,
        today: date | None = None,
    ) -> None:
        if client is None:
            if not api_key or not access_token:
                raise KiteError(
                    "KiteMarketData needs either an injected client or both "
                    "api_key and access_token."
                )
            client = _build_client(api_key, access_token)
        self._client = client
        self._today = today or date.today()
        self._token_cache: dict[str, int] = {}

    # -- MarketDataPort ---------------------------------------------------

    def get_quote(self, instrument: Instrument) -> Quote:
        data = self._quote_payload(instrument)
        ohlc = data.get("ohlc") or {}
        last_price = _to_float(data.get("last_price"))
        return Quote(
            instrument=instrument,
            last_price=last_price,
            day_high=_to_float(ohlc.get("high", last_price)),
            day_low=_to_float(ohlc.get("low", last_price)),
            volume=int(data.get("volume") or data.get("volume_traded") or 0),
        )

    def get_candles(self, instrument: Instrument, *, days: int) -> list[Candle]:
        token = self._instrument_token(instrument)
        span = max(1, min(days, _MAX_DAYS))
        # Widen the calendar window so weekends/holidays still leave enough bars.
        from_date = self._today - timedelta(days=int(span * 1.6) + 10)
        rows = self._client.historical_data(
            instrument_token=token,
            from_date=datetime.combine(from_date, datetime.min.time()),
            to_date=datetime.combine(self._today, datetime.min.time()),
            interval="day",
        )
        candles = [self._to_candle(row) for row in rows]
        return candles[-span:]

    # -- internals --------------------------------------------------------

    def _quote_payload(self, instrument: Instrument) -> dict[str, Any]:
        key = instrument.key
        try:
            response = self._client.quote([key])
        except Exception as exc:  # noqa: BLE001 - surface any SDK/network error uniformly
            raise KiteError(f"Kite quote failed for {key}: {exc}") from exc
        if key not in response:
            raise KiteError(f"Kite returned no quote for {key}")
        return response[key]

    def _instrument_token(self, instrument: Instrument) -> int:
        key = instrument.key
        if key not in self._token_cache:
            payload = self._quote_payload(instrument)
            token = payload.get("instrument_token")
            if not token:
                raise KiteError(f"No instrument_token in Kite quote for {key}")
            self._token_cache[key] = int(token)
        return self._token_cache[key]

    @staticmethod
    def _to_candle(row: dict[str, Any]) -> Candle:
        raw_date = row["date"]
        on = raw_date.date() if isinstance(raw_date, datetime) else _parse_date(raw_date)
        return Candle(
            on=on,
            open=_to_float(row["open"]),
            high=_to_float(row["high"]),
            low=_to_float(row["low"]),
            close=_to_float(row["close"]),
            volume=int(row.get("volume") or 0),
        )


def _to_float(value: Any) -> float:
    if value is None:
        raise KiteError("Expected a numeric value from Kite but got None")
    return float(value)


def _parse_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(str(value)[:10]).date()
