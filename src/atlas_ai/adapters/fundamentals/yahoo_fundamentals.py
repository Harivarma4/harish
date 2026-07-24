"""Public fundamentals adapter backed by Yahoo Finance ``quoteSummary`` (no key).

Yahoo publishes a summary of company financials for free. This implements
``FundamentalsPort`` by mapping the ``quoteSummary`` modules onto the domain
``Fundamentals`` object.

Honest gaps (Yahoo does not expose these): **ROCE** is approximated from return
on assets, **promoter holding** is approximated from Yahoo's insider-held
percentage, and **promoter pledge** is not available and defaults to 0. Use the
``file`` fundamentals source when you need exact promoter/pledge figures from
NSE/BSE disclosures. Core valuation/quality fields (market cap, P/E, P/B, ROE)
are required — a fetch missing them raises rather than fabricating.

Like the market-data adapter, it needs outbound access to
``query1.finance.yahoo.com`` (blocked by restricted-network sandboxes) and its
HTTP client is injectable, so the mapping is fully unit-tested offline. Note that
Yahoo's quoteSummary endpoint may require a session cookie/crumb from some
networks; supplying a pre-configured client handles that where needed.
"""

from __future__ import annotations

from typing import Any

from atlas_ai.adapters.yahoo_common import (
    USER_AGENT,
    HttpGetClient,
    HttpxClient,
    YahooError,
    ticker_for,
)
from atlas_ai.domain.market import Fundamentals, Instrument

__all__ = ["YahooError", "YahooFundamentals"]

_BASE = "https://query1.finance.yahoo.com/v10/finance/quoteSummary"
_MODULES = "financialData,defaultKeyStatistics,summaryDetail,price"


class YahooFundamentals:
    """Company fundamentals from the public Yahoo Finance quoteSummary API."""

    def __init__(self, *, client: HttpGetClient | None = None) -> None:
        self._client = client if client is not None else HttpxClient()

    def get_fundamentals(self, instrument: Instrument) -> Fundamentals:
        result = self._fetch(instrument)
        fin = result.get("financialData") or {}
        key = result.get("defaultKeyStatistics") or {}
        summ = result.get("summaryDetail") or {}
        price = result.get("price") or {}
        ticker = ticker_for(instrument)

        # Core valuation/quality fields are required — never fabricated.
        market_cap = _require(
            _raw(price, "marketCap") or _raw(summ, "marketCap"), "marketCap", ticker
        )
        pe = _require(_raw(summ, "trailingPE") or _raw(key, "trailingPE"), "trailingPE", ticker)
        pb = _require(_raw(key, "priceToBook"), "priceToBook", ticker)
        roe = _require(_pct(_raw(fin, "returnOnEquity")), "returnOnEquity", ticker)

        roa = _pct(_raw(fin, "returnOnAssets"))
        earnings_growth = _pct(_raw(fin, "earningsGrowth"))
        if earnings_growth is None:
            earnings_growth = _pct(_raw(key, "earningsQuarterlyGrowth"))

        return Fundamentals(
            instrument=instrument,
            market_cap_cr=round(market_cap / 1e7, 2),          # rupees -> crores
            pe=round(pe, 2),
            pb=round(pb, 2),
            roe_pct=round(roe, 2),
            roce_pct=round(roa if roa is not None else roe, 2),  # ROA proxy for ROCE
            debt_to_equity=_debt_to_equity(_raw(fin, "debtToEquity")),
            operating_margin_pct=round(_pct(_raw(fin, "operatingMargins")) or 0.0, 2),
            net_margin_pct=round(_pct(_raw(fin, "profitMargins")) or 0.0, 2),
            revenue_growth_pct=round(_pct(_raw(fin, "revenueGrowth")) or 0.0, 2),
            earnings_growth_pct=round(earnings_growth or 0.0, 2),
            dividend_yield_pct=round(_pct(_raw(summ, "dividendYield")) or 0.0, 2),
            promoter_holding_pct=round(_pct(_raw(key, "heldPercentInsiders")) or 0.0, 2),
            promoter_pledge_pct=0.0,  # not available on Yahoo
        )

    def _fetch(self, instrument: Instrument) -> dict[str, Any]:
        ticker = ticker_for(instrument)
        url = f"{_BASE}/{ticker}"
        params = {"modules": _MODULES}
        try:
            resp = self._client.get(url, params=params, headers={"User-Agent": USER_AGENT})
        except Exception as exc:  # noqa: BLE001 - surface any client/network error uniformly
            raise YahooError(f"Yahoo request failed for {ticker}: {exc}") from exc

        if resp.status_code != 200:
            raise YahooError(f"Yahoo returned HTTP {resp.status_code} for {ticker}")
        summary = (resp.json() or {}).get("quoteSummary") or {}
        if summary.get("error"):
            raise YahooError(f"Yahoo error for {ticker}: {summary['error']}")
        results = summary.get("result") or []
        if not results:
            raise YahooError(f"Yahoo returned no fundamentals for {ticker}")
        first: dict[str, Any] = results[0]
        return first


def _require(value: float | None, name: str, ticker: str) -> float:
    """Return a required numeric value, or raise if Yahoo omitted it."""
    if value is None:
        raise YahooError(f"Yahoo fundamentals for {ticker} missing core field: {name}")
    return value


def _raw(module: dict[str, Any], field: str) -> float | None:
    """Pull the numeric ``raw`` value out of a Yahoo ``{raw, fmt}`` node."""
    node = module.get(field)
    if node is None:
        return None
    if isinstance(node, dict):
        node = node.get("raw")
    if node is None:
        return None
    try:
        return float(node)
    except (TypeError, ValueError):
        return None


def _pct(fraction: float | None) -> float | None:
    """Yahoo expresses ratios as fractions (0.18); convert to a percentage."""
    return None if fraction is None else fraction * 100.0


def _debt_to_equity(value: float | None) -> float:
    """Yahoo reports D/E as a percentage-like number (e.g. 42.5 => 0.425 ratio).
    Values above ~5 are treated as percentages; smaller ones as ratios."""
    if value is None:
        return 0.0
    return round(value / 100.0 if value > 5 else value, 3)
