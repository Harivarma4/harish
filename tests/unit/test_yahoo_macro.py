"""YahooMacro adapter — offline via a fake HTTP client."""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from atlas_ai.adapters.macro.yahoo_macro import YahooMacro
from atlas_ai.adapters.yahoo_common import YahooError


class FakeResponse:
    def __init__(self, payload: Any, status_code: int = 200) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> Any:
        return self._payload


class FakeHttp:
    """Returns a per-symbol close series keyed by the URL's ticker."""

    def __init__(self, series: dict[str, list[float]]) -> None:
        self._series = series
        self.symbols: list[str] = []

    def get(self, url: str, *, params: dict[str, Any], headers: dict[str, str]) -> FakeResponse:
        symbol = url.rsplit("/", 1)[-1]
        self.symbols.append(symbol)
        closes = self._series.get(symbol)
        if closes is None:
            return FakeResponse({"chart": {"error": "Not Found", "result": None}}, 404)
        payload = {"chart": {"error": None, "result": [
            {"indicators": {"quote": [{"close": closes}]}}
        ]}}
        return FakeResponse(payload)


def _macro(http: FakeHttp) -> YahooMacro:
    return YahooMacro(
        repo_rate_pct=6.5, cpi_inflation_pct=5.1, gdp_growth_pct=6.8,
        india_10y_yield_pct=7.0, fii_flow_cr=-1500.0,
        client=http, today=date(2026, 1, 15),
    )


def test_combines_live_vars_with_config_figures() -> None:
    http = FakeHttp({
        "INR=X": [83.5, 84.0, 84.6],
        "BZ=F": [80.0, 81.0, 82.5],
        "^GSPC": [5000.0, 5050.0, 5100.0],   # +2.0% over the window
    })
    snap = _macro(http).get_snapshot()
    # Live market vars from Yahoo:
    assert snap.usd_inr == 84.6
    assert snap.crude_oil_usd == 82.5
    assert snap.global_equity_trend_pct == 2.0
    # Official figures from config:
    assert snap.repo_rate_pct == 6.5
    assert snap.cpi_inflation_pct == 5.1
    assert snap.fii_flow_cr == -1500.0
    assert snap.as_of == date(2026, 1, 15)
    assert set(http.symbols) == {"INR=X", "BZ=F", "^GSPC"}


def test_fetch_failure_raises() -> None:
    http = FakeHttp({"INR=X": [84.0]})  # crude + global missing -> 404
    with pytest.raises(YahooError):
        _macro(http).get_snapshot()
