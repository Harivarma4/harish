"""Real macro adapter — live market-derived vars + configured official figures.

Yahoo publishes the *market* macro variables for free (rupee ``INR=X``, Brent
crude ``BZ=F``, and a global-equity proxy ``^GSPC``). The *policy* figures — RBI
repo rate, CPI, GDP growth, the India 10Y yield, and net FII flow — are not on a
free price API; they are official releases (RBI / MOSPI / NSE), so they come from
configuration and are updated when new prints land. This is genuinely real data:
live market vars + the latest official numbers you configure.

Needs outbound access to ``query1.finance.yahoo.com`` (firewalled in restricted
sandboxes). The HTTP client is injectable, so the parsing is unit-tested offline.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from atlas_ai.adapters.yahoo_common import (
    USER_AGENT,
    HttpGetClient,
    HttpxClient,
    YahooError,
)
from atlas_ai.domain.macro import MacroIndicators

_BASE = "https://query1.finance.yahoo.com/v8/finance/chart"
_USDINR = "INR=X"
_BRENT = "BZ=F"
_GLOBAL = "^GSPC"  # S&P 500, a standard global risk proxy


class YahooMacro:
    """Assembles a MacroIndicators snapshot from live Yahoo vars + config figures."""

    def __init__(
        self,
        *,
        repo_rate_pct: float,
        cpi_inflation_pct: float,
        gdp_growth_pct: float,
        india_10y_yield_pct: float,
        fii_flow_cr: float,
        client: HttpGetClient | None = None,
        today: date | None = None,
    ) -> None:
        self._client = client if client is not None else HttpxClient()
        self._repo = repo_rate_pct
        self._cpi = cpi_inflation_pct
        self._gdp = gdp_growth_pct
        self._yield = india_10y_yield_pct
        self._fii = fii_flow_cr
        self._today = today or datetime.now(UTC).date()

    def get_snapshot(self) -> MacroIndicators:
        usd_inr = self._last(_USDINR)
        crude = self._last(_BRENT)
        global_trend = self._change_pct(_GLOBAL)
        return MacroIndicators(
            repo_rate_pct=self._repo,
            cpi_inflation_pct=self._cpi,
            gdp_growth_pct=self._gdp,
            india_10y_yield_pct=self._yield,
            usd_inr=round(usd_inr, 4),
            crude_oil_usd=round(crude, 2),
            fii_flow_cr=self._fii,
            global_equity_trend_pct=round(global_trend, 2),
            as_of=self._today,
        )

    def _closes(self, symbol: str) -> list[float]:
        try:
            resp = self._client.get(
                f"{_BASE}/{symbol}",
                params={"range": "1mo", "interval": "1d"},
                headers={"User-Agent": USER_AGENT},
            )
        except Exception as exc:  # noqa: BLE001 - surface any client/network error uniformly
            raise YahooError(f"Macro fetch failed for {symbol}: {exc}") from exc
        if resp.status_code != 200:
            raise YahooError(f"Macro fetch HTTP {resp.status_code} for {symbol}")
        chart = (resp.json() or {}).get("chart") or {}
        results = chart.get("result") or []
        if chart.get("error") or not results:
            raise YahooError(f"Macro fetch returned no data for {symbol}")
        quote = ((results[0].get("indicators") or {}).get("quote") or [{}])[0]
        closes = [c for c in (quote.get("close") or []) if c is not None]
        if not closes:
            raise YahooError(f"Macro fetch had no closes for {symbol}")
        return [float(c) for c in closes]

    def _last(self, symbol: str) -> float:
        return self._closes(symbol)[-1]

    def _change_pct(self, symbol: str) -> float:
        closes = self._closes(symbol)
        first, last = closes[0], closes[-1]
        return (last - first) / first * 100.0 if first else 0.0
