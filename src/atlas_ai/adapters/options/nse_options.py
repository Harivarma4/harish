"""Real option-chain adapter — the public NSE option-chain endpoint.

NSE publishes a free, key-less option-chain JSON API. It is heavily bot-protected:
a browser-like ``User-Agent`` and a warm-up cookie from ``nseindia.com`` are
required, and it is unreachable from firewalled sandboxes (works where deployed
with outbound access to ``www.nseindia.com``). The HTTP client is injectable so
parsing is unit-tested offline.

Implied volatility is reported in percent and normalised to a fraction here. Any
failure (network, shape, empty chain) returns ``None`` — the options agent treats
that as a neutral, no-signal report rather than failing the recommendation.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any, Protocol, runtime_checkable

from atlas_ai.domain.market import Instrument
from atlas_ai.domain.options import OptionChain, OptionQuote, OptionRight

logger = logging.getLogger("atlas_ai.options")

_HOME = "https://www.nseindia.com"
_EQUITIES = "https://www.nseindia.com/api/option-chain-equities"
_INDICES = "https://www.nseindia.com/api/option-chain-indices"
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
# Map domain index symbols/tickers to NSE index names.
_INDEX_NAMES = {
    "NIFTY": "NIFTY", "^NSEI": "NIFTY", "NIFTY50": "NIFTY",
    "BANKNIFTY": "BANKNIFTY", "^NSEBANK": "BANKNIFTY",
    "FINNIFTY": "FINNIFTY", "MIDCPNIFTY": "MIDCPNIFTY",
}


@runtime_checkable
class JsonResponse(Protocol):
    @property
    def status_code(self) -> int: ...

    def json(self) -> Any: ...


@runtime_checkable
class JsonClient(Protocol):
    def get(self, url: str, *, params: dict[str, str], headers: dict[str, str]) -> JsonResponse: ...

    def warm_up(self, url: str, *, headers: dict[str, str]) -> None: ...


class HttpxJsonClient:
    """Default ``JsonClient`` backed by httpx with a persistent cookie jar."""

    def __init__(self, *, timeout: float = 15.0) -> None:
        import httpx

        self._client = httpx.Client(timeout=timeout, headers={"User-Agent": _UA})

    def warm_up(self, url: str, *, headers: dict[str, str]) -> None:
        self._client.get(url, headers=headers)

    def get(self, url: str, *, params: dict[str, str], headers: dict[str, str]) -> JsonResponse:
        return self._client.get(url, params=params, headers=headers)


class NseOptions:
    """Satisfies ``OptionsPort`` using the public NSE option-chain endpoint."""

    def __init__(self, *, client: JsonClient | None = None) -> None:
        self._client = client if client is not None else HttpxJsonClient()

    def get_chain(self, instrument: Instrument) -> OptionChain | None:
        symbol = instrument.symbol.upper()
        index_name = _INDEX_NAMES.get(symbol)
        url = _INDICES if index_name else _EQUITIES
        params = {"symbol": index_name or symbol}
        headers = {"User-Agent": _UA, "Accept": "application/json"}
        try:
            # NSE needs a home-page visit first to mint anti-bot cookies.
            self._client.warm_up(_HOME, headers={"User-Agent": _UA})
            resp = self._client.get(url, params=params, headers=headers)
            if resp.status_code != 200:
                logger.warning("NSE option chain HTTP %s for %s", resp.status_code, symbol)
                return None
            return self._parse(instrument, resp.json())
        except Exception as exc:  # noqa: BLE001 - options must never break a recommendation
            logger.warning("NSE option chain fetch failed for %s: %s", symbol, exc)
            return None

    def _parse(self, instrument: Instrument, payload: Any) -> OptionChain | None:
        records = payload.get("records") if isinstance(payload, dict) else None
        if not isinstance(records, dict):
            return None
        rows = records.get("data") or []
        expiries = records.get("expiryDates") or []
        spot = float(records.get("underlyingValue") or 0.0)
        if not rows or not expiries or spot <= 0.0:
            return None
        expiry_raw = expiries[0]
        expiry = _parse_date(expiry_raw)
        if expiry is None:
            return None

        calls: list[OptionQuote] = []
        puts: list[OptionQuote] = []
        for row in rows:
            if not isinstance(row, dict) or row.get("expiryDate") != expiry_raw:
                continue
            strike = _num(row.get("strikePrice"))
            if strike is None:
                continue
            ce = row.get("CE")
            pe = row.get("PE")
            if isinstance(ce, dict):
                calls.append(_quote(strike, OptionRight.CALL, ce))
            if isinstance(pe, dict):
                puts.append(_quote(strike, OptionRight.PUT, pe))
        if not calls or not puts:
            return None
        return OptionChain(
            instrument=instrument,
            spot=spot,
            expiry=expiry,
            as_of=date.today(),  # noqa: DTZ011 - trade date, tz-naive is fine
            calls=tuple(calls),
            puts=tuple(puts),
        )


def _quote(strike: float, right: OptionRight, leg: dict[str, Any]) -> OptionQuote:
    return OptionQuote(
        strike=strike,
        right=right,
        last_price=_num(leg.get("lastPrice")) or 0.0,
        open_interest=_num(leg.get("openInterest")) or 0.0,
        implied_volatility=(_num(leg.get("impliedVolatility")) or 0.0) / 100.0,
        volume=_num(leg.get("totalTradedVolume")) or 0.0,
        change_in_oi=_num(leg.get("changeinOpenInterest")) or 0.0,
    )


def _num(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_date(raw: Any) -> date | None:
    if not isinstance(raw, str):
        return None
    try:
        return datetime.strptime(raw, "%d-%b-%Y").date()  # noqa: DTZ007 - date only
    except ValueError:
        return None
