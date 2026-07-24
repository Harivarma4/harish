"""Shared building blocks for the public Yahoo Finance adapters.

Both the market-data adapter (prices/candles) and the fundamentals adapter reuse
the same injectable HTTP surface, ticker mapping, and error type.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from atlas_ai.domain.enums import Exchange
from atlas_ai.domain.market import Instrument

USER_AGENT = "Mozilla/5.0 (compatible; AtlasAI/0.1; +research-tool)"
_SUFFIX = {Exchange.NSE: ".NS", Exchange.BSE: ".BO"}


class YahooError(RuntimeError):
    """Raised for adapter-level failures talking to Yahoo Finance."""


@runtime_checkable
class Response(Protocol):
    status_code: int

    def json(self) -> Any: ...


@runtime_checkable
class HttpGetClient(Protocol):
    """Minimal HTTP GET surface (satisfied by ``httpx.Client``)."""

    def get(
        self, url: str, *, params: dict[str, Any], headers: dict[str, str]
    ) -> Response: ...


class HttpxClient:
    """Default ``HttpGetClient`` backed by httpx (a base dependency)."""

    def __init__(self, *, timeout: float = 15.0) -> None:
        import httpx

        self._client = httpx.Client(timeout=timeout, headers={"User-Agent": USER_AGENT})

    def get(
        self, url: str, *, params: dict[str, Any], headers: dict[str, str]
    ) -> Response:
        return self._client.get(url, params=params, headers=headers)


def ticker_for(instrument: Instrument) -> str:
    """Map a domain instrument to a Yahoo ticker.

    NSE → ``<SYMBOL>.NS``, BSE → ``<SYMBOL>.BO``, and a leading ``^`` symbol
    (e.g. ``^NSEI`` for Nifty 50) is passed through as an index ticker.
    """
    symbol = instrument.symbol.upper()
    if symbol.startswith("^"):
        return symbol
    return f"{symbol}{_SUFFIX[instrument.exchange]}"
