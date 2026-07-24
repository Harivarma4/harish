"""Public market-data adapter backed by Yahoo Finance (no API key).

Yahoo's chart endpoint publishes historical daily OHLCV for Indian equities and
indices for free — NSE symbols as ``<SYMBOL>.NS`` and BSE as ``<SYMBOL>.BO`` (a
leading ``^`` symbol, e.g. ``^NSEI`` for Nifty 50, is passed through as an index
ticker). This implements ``MarketDataPort`` (quotes + candles) — the same
interface as the mock and Kite adapters.

It needs outbound access to ``query1.finance.yahoo.com``. Sandboxes with a
restricted network policy block that host, so it runs where you deploy it (your
machine, or any environment where the host is reachable). The HTTP client is
injectable behind an ``HttpGetClient`` Protocol, so the URL-building and
JSON-parsing logic is fully unit-tested offline with a fake client.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from typing import Any, Protocol, runtime_checkable

from atlas_ai.domain.enums import Exchange
from atlas_ai.domain.market import Candle, Instrument, Quote

_BASE = "https://query1.finance.yahoo.com/v8/finance/chart"
_UA = "Mozilla/5.0 (compatible; AtlasAI/0.1; +research-tool)"
_SUFFIX = {Exchange.NSE: ".NS", Exchange.BSE: ".BO"}


@runtime_checkable
class _Response(Protocol):
    status_code: int

    def json(self) -> Any: ...


@runtime_checkable
class HttpGetClient(Protocol):
    """Minimal HTTP GET surface (satisfied by ``httpx.Client``)."""

    def get(
        self, url: str, *, params: dict[str, Any], headers: dict[str, str]
    ) -> _Response: ...


class YahooError(RuntimeError):
    """Raised for adapter-level failures talking to Yahoo Finance."""


class _HttpxClient:
    """Default ``HttpGetClient`` backed by httpx (a base dependency)."""

    def __init__(self, *, timeout: float = 15.0) -> None:
        import httpx

        self._client = httpx.Client(timeout=timeout, headers={"User-Agent": _UA})

    def get(
        self, url: str, *, params: dict[str, Any], headers: dict[str, str]
    ) -> _Response:
        return self._client.get(url, params=params, headers=headers)


def _ticker(instrument: Instrument) -> str:
    symbol = instrument.symbol.upper()
    if symbol.startswith("^"):  # index ticker, e.g. ^NSEI (Nifty 50)
        return symbol
    return f"{symbol}{_SUFFIX[instrument.exchange]}"


def _epoch(d: date) -> int:
    return int(datetime.combine(d, time(), tzinfo=UTC).timestamp())


class YahooMarketData:
    """Real quotes and daily candles from the public Yahoo Finance API."""

    def __init__(
        self, *, client: HttpGetClient | None = None, today: date | None = None
    ) -> None:
        self._client = client if client is not None else _HttpxClient()
        self._today = today or datetime.now(UTC).date()

    # -- MarketDataPort ---------------------------------------------------

    def get_candles(self, instrument: Instrument, *, days: int) -> list[Candle]:
        span = max(1, days)
        # Widen the calendar window so weekends/holidays still leave enough bars.
        start = self._today - timedelta(days=int(span * 1.6) + 10)
        result = self._fetch(instrument, start=start)
        return self._candles(result)[-span:]

    def get_quote(self, instrument: Instrument) -> Quote:
        result = self._fetch(instrument, start=self._today - timedelta(days=14))
        meta = result.get("meta") or {}
        candles = self._candles(result)
        last = candles[-1] if candles else None

        last_price = meta.get("regularMarketPrice")
        if last_price is None and last is not None:
            last_price = last.close
        if last_price is None:
            raise YahooError(f"No price available for {_ticker(instrument)}")

        return Quote(
            instrument=instrument,
            last_price=float(last_price),
            day_high=float(meta.get("regularMarketDayHigh") or (last.high if last else last_price)),
            day_low=float(meta.get("regularMarketDayLow") or (last.low if last else last_price)),
            volume=int(meta.get("regularMarketVolume") or (last.volume if last else 0)),
        )

    # -- internals --------------------------------------------------------

    def _fetch(self, instrument: Instrument, *, start: date) -> dict[str, Any]:
        ticker = _ticker(instrument)
        url = f"{_BASE}/{ticker}"
        params = {
            "period1": _epoch(start),
            "period2": _epoch(self._today) + 86_400,
            "interval": "1d",
        }
        try:
            resp = self._client.get(url, params=params, headers={"User-Agent": _UA})
        except Exception as exc:  # noqa: BLE001 - surface any client/network error uniformly
            raise YahooError(f"Yahoo request failed for {ticker}: {exc}") from exc

        if resp.status_code != 200:
            raise YahooError(f"Yahoo returned HTTP {resp.status_code} for {ticker}")
        chart = (resp.json() or {}).get("chart") or {}
        if chart.get("error"):
            raise YahooError(f"Yahoo error for {ticker}: {chart['error']}")
        results = chart.get("result") or []
        if not results:
            raise YahooError(f"Yahoo returned no data for {ticker}")
        first: dict[str, Any] = results[0]
        return first

    @staticmethod
    def _candles(result: dict[str, Any]) -> list[Candle]:
        timestamps = result.get("timestamp") or []
        quote = ((result.get("indicators") or {}).get("quote") or [{}])[0]
        opens = quote.get("open") or []
        highs = quote.get("high") or []
        lows = quote.get("low") or []
        closes = quote.get("close") or []
        volumes = quote.get("volume") or []

        candles: list[Candle] = []
        for i, ts in enumerate(timestamps):
            close = closes[i] if i < len(closes) else None
            if close is None:  # market holiday / gap row
                continue
            open_ = opens[i] if i < len(opens) and opens[i] is not None else close
            high = highs[i] if i < len(highs) and highs[i] is not None else close
            low = lows[i] if i < len(lows) and lows[i] is not None else close
            volume = volumes[i] if i < len(volumes) and volumes[i] is not None else 0
            candles.append(
                Candle(
                    on=datetime.fromtimestamp(ts, tz=UTC).date(),
                    open=round(float(open_), 2),
                    high=round(float(high), 2),
                    low=round(float(low), 2),
                    close=round(float(close), 2),
                    volume=int(volume),
                )
            )
        return candles
