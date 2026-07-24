"""KiteMarketData adapter logic, exercised offline via a fake Kite client.

We can't reach the live Kite API in tests, so we inject a fake client that
mimics the shapes ``kiteconnect.KiteConnect`` returns and assert the adapter maps
them correctly onto the domain (Quote/Candle) and handles errors.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import pytest

from atlas_ai.adapters.market_data.kite_market_data import KiteError, KiteMarketData
from atlas_ai.domain.enums import Exchange
from atlas_ai.domain.market import Instrument

INSTRUMENT = Instrument("RELIANCE", Exchange.NSE)


class FakeKite:
    """Mimics the subset of KiteConnect used by the adapter."""

    def __init__(
        self,
        *,
        quote_payload: dict[str, Any] | None = None,
        candles: list[dict[str, Any]] | None = None,
    ) -> None:
        self._quote_payload = quote_payload
        self._candles = candles or []
        self.quote_calls: list[list[str]] = []
        self.historical_calls: list[tuple[int, str]] = []

    def quote(self, instruments: list[str]) -> dict[str, Any]:
        self.quote_calls.append(instruments)
        if self._quote_payload is None:
            return {}
        return {instruments[0]: self._quote_payload}

    def historical_data(
        self, instrument_token: int, from_date: Any, to_date: Any, interval: str,
        continuous: bool = False, oi: bool = False,
    ) -> list[dict[str, Any]]:
        self.historical_calls.append((instrument_token, interval))
        return self._candles


def _quote_payload() -> dict[str, Any]:
    return {
        "instrument_token": 738561,
        "last_price": 2950.5,
        "volume": 12_345_678,
        "ohlc": {"open": 2900.0, "high": 2965.0, "low": 2890.0, "close": 2925.0},
    }


def _candle_rows(n: int) -> list[dict[str, Any]]:
    return [
        {
            "date": datetime(2026, 1, 1 + i),
            "open": 100.0 + i,
            "high": 101.0 + i,
            "low": 99.0 + i,
            "close": 100.5 + i,
            "volume": 1_000_000 + i,
        }
        for i in range(n)
    ]


def test_get_quote_maps_fields() -> None:
    client = FakeKite(quote_payload=_quote_payload())
    adapter = KiteMarketData(client=client)
    quote = adapter.get_quote(INSTRUMENT)
    assert quote.last_price == 2950.5
    assert quote.day_high == 2965.0
    assert quote.day_low == 2890.0
    assert quote.volume == 12_345_678
    assert client.quote_calls == [["NSE:RELIANCE"]]


def test_get_candles_maps_and_truncates() -> None:
    client = FakeKite(quote_payload=_quote_payload(), candles=_candle_rows(30))
    adapter = KiteMarketData(client=client, today=date(2026, 2, 1))
    candles = adapter.get_candles(INSTRUMENT, days=10)
    assert len(candles) == 10  # truncated to the requested span
    last = candles[-1]
    assert last.close == 100.5 + 29
    assert last.on == date(2026, 1, 30)
    # historical_data is called with the resolved token and daily interval.
    assert client.historical_calls == [(738561, "day")]


def test_token_is_resolved_once_and_cached() -> None:
    client = FakeKite(quote_payload=_quote_payload(), candles=_candle_rows(5))
    adapter = KiteMarketData(client=client)
    adapter.get_candles(INSTRUMENT, days=5)
    adapter.get_candles(INSTRUMENT, days=5)
    # First candles call resolves the token via quote; second reuses the cache.
    assert len(client.quote_calls) == 1


def test_missing_quote_raises() -> None:
    adapter = KiteMarketData(client=FakeKite(quote_payload=None))
    with pytest.raises(KiteError):
        adapter.get_quote(INSTRUMENT)


def test_requires_client_or_credentials() -> None:
    with pytest.raises(KiteError):
        KiteMarketData()


def test_iso_string_dates_are_parsed() -> None:
    rows = [
        {"date": "2026-01-05T00:00:00+0530", "open": 1, "high": 2, "low": 0.5,
         "close": 1.5, "volume": 10},
    ]
    client = FakeKite(quote_payload=_quote_payload(), candles=rows)
    adapter = KiteMarketData(client=client)
    candles = adapter.get_candles(INSTRUMENT, days=5)
    assert candles[0].on == date(2026, 1, 5)
