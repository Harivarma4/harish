"""YahooMarketData adapter logic, exercised offline via a fake HTTP client.

Yahoo Finance can't be reached in tests (and is firewalled in the sandbox), so we
inject a fake client that returns canned chart-endpoint JSON and assert the
adapter builds the right ticker/URL and parses OHLCV correctly.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

import pytest

from atlas_ai.adapters.market_data.yahoo_market_data import YahooError, YahooMarketData
from atlas_ai.domain.enums import Exchange
from atlas_ai.domain.market import Instrument

RELIANCE = Instrument("RELIANCE", Exchange.NSE)


class FakeResponse:
    def __init__(self, payload: Any, status_code: int = 200) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> Any:
        return self._payload


class FakeHttp:
    def __init__(self, response: FakeResponse) -> None:
        self._response = response
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def get(self, url: str, *, params: dict[str, Any], headers: dict[str, str]) -> FakeResponse:
        self.calls.append((url, params))
        return self._response


def _epoch(y: int, m: int, d: int) -> int:
    return int(datetime(y, m, d, tzinfo=UTC).timestamp())


def _chart_payload(
    n: int, *, symbol: str = "RELIANCE.NS", with_gap: bool = False
) -> dict[str, Any]:
    ts = [_epoch(2026, 1, 1 + i) for i in range(n)]
    close = [100.0 + i for i in range(n)]
    if with_gap:
        close[1] = None  # simulate a holiday row
    return {
        "chart": {
            "error": None,
            "result": [
                {
                    "meta": {
                        "symbol": symbol,
                        "regularMarketPrice": 128.5,
                        "regularMarketDayHigh": 130.0,
                        "regularMarketDayLow": 126.0,
                        "regularMarketVolume": 5_000_000,
                    },
                    "timestamp": ts,
                    "indicators": {
                        "quote": [
                            {
                                "open": [c - 0.5 if c is not None else None for c in close],
                                "high": [c + 1 if c is not None else None for c in close],
                                "low": [c - 1 if c is not None else None for c in close],
                                "close": close,
                                "volume": [1_000_000 + i for i in range(n)],
                            }
                        ]
                    },
                }
            ],
        }
    }


def test_nse_ticker_and_candles() -> None:
    http = FakeHttp(FakeResponse(_chart_payload(30)))
    adapter = YahooMarketData(client=http, today=date(2026, 2, 1))
    candles = adapter.get_candles(RELIANCE, days=10)
    assert len(candles) == 10          # truncated to requested span
    assert candles[-1].close == 100.0 + 29
    url, _ = http.calls[0]
    assert url.endswith("/RELIANCE.NS")  # NSE -> .NS suffix


def test_bse_and_index_tickers() -> None:
    http = FakeHttp(FakeResponse(_chart_payload(5, symbol="TCS.BO")))
    YahooMarketData(client=http).get_candles(Instrument("TCS", Exchange.BSE), days=5)
    assert http.calls[0][0].endswith("/TCS.BO")   # BSE -> .BO

    http2 = FakeHttp(FakeResponse(_chart_payload(5, symbol="^NSEI")))
    YahooMarketData(client=http2).get_candles(Instrument("^NSEI", Exchange.NSE), days=5)
    assert http2.calls[0][0].endswith("/^NSEI")   # index passthrough


def test_holiday_rows_are_skipped() -> None:
    http = FakeHttp(FakeResponse(_chart_payload(10, with_gap=True)))
    candles = YahooMarketData(client=http).get_candles(RELIANCE, days=10)
    assert len(candles) == 9  # the null-close row is dropped


def test_quote_uses_meta() -> None:
    http = FakeHttp(FakeResponse(_chart_payload(15)))
    quote = YahooMarketData(client=http).get_quote(RELIANCE)
    assert quote.last_price == 128.5
    assert quote.day_high == 130.0
    assert quote.volume == 5_000_000


def test_http_error_raises() -> None:
    http = FakeHttp(FakeResponse({}, status_code=403))
    with pytest.raises(YahooError):
        YahooMarketData(client=http).get_candles(RELIANCE, days=5)


def test_chart_error_raises() -> None:
    payload = {"chart": {"error": {"code": "Not Found"}, "result": None}}
    with pytest.raises(YahooError):
        YahooMarketData(client=FakeHttp(FakeResponse(payload))).get_candles(RELIANCE, days=5)
