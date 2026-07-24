"""YahooFundamentals adapter logic, exercised offline via a fake HTTP client."""

from __future__ import annotations

from typing import Any

import pytest

from atlas_ai.adapters.fundamentals.yahoo_fundamentals import YahooError, YahooFundamentals
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


def _r(v: float) -> dict[str, Any]:
    return {"raw": v, "fmt": str(v)}


def _payload(**overrides: Any) -> dict[str, Any]:
    result = {
        "price": {"marketCap": _r(19_000_000_000_000)},   # ~19,00,000 cr
        "summaryDetail": {"trailingPE": _r(24.0), "dividendYield": _r(0.004)},
        "defaultKeyStatistics": {"priceToBook": _r(2.3), "heldPercentInsiders": _r(0.503)},
        "financialData": {
            "returnOnEquity": _r(0.09),
            "returnOnAssets": _r(0.055),
            "debtToEquity": _r(42.5),          # percentage form -> 0.425
            "operatingMargins": _r(0.17),
            "profitMargins": _r(0.08),
            "revenueGrowth": _r(0.10),
            "earningsGrowth": _r(0.11),
        },
    }
    result.update(overrides)
    return {"quoteSummary": {"error": None, "result": [result]}}


def test_maps_fields_and_units() -> None:
    http = FakeHttp(FakeResponse(_payload()))
    f = YahooFundamentals(client=http).get_fundamentals(RELIANCE)
    assert f.market_cap_cr == 1_900_000.0       # rupees -> crores
    assert f.pe == 24.0 and f.pb == 2.3
    assert f.roe_pct == 9.0                      # fraction -> percent
    assert f.roce_pct == 5.5                     # ROA proxy
    assert f.debt_to_equity == 0.425            # percentage form normalized
    assert f.operating_margin_pct == 17.0
    assert f.net_margin_pct == 8.0
    assert f.revenue_growth_pct == 10.0
    assert f.earnings_growth_pct == 11.0
    assert f.dividend_yield_pct == 0.4
    assert f.promoter_holding_pct == 50.3        # insiders proxy
    assert f.promoter_pledge_pct == 0.0          # unavailable on Yahoo
    # ticker + endpoint
    url, params = http.calls[0]
    assert url.endswith("/RELIANCE.NS")
    assert "financialData" in params["modules"]


def test_debt_to_equity_ratio_form_passthrough() -> None:
    payload = _payload(financialData={
        "returnOnEquity": _r(0.2), "debtToEquity": _r(0.35),
    })
    f = YahooFundamentals(client=FakeHttp(FakeResponse(payload))).get_fundamentals(RELIANCE)
    assert f.debt_to_equity == 0.35   # already a ratio -> unchanged


def test_missing_core_field_raises() -> None:
    payload = _payload(summaryDetail={"dividendYield": _r(0.01)})  # no trailingPE
    with pytest.raises(YahooError, match="trailingPE"):
        YahooFundamentals(client=FakeHttp(FakeResponse(payload))).get_fundamentals(RELIANCE)


def test_http_error_raises() -> None:
    with pytest.raises(YahooError):
        YahooFundamentals(client=FakeHttp(FakeResponse({}, status_code=404))).get_fundamentals(
            RELIANCE
        )


def test_soft_fields_default_when_absent() -> None:
    payload = _payload(financialData={
        "returnOnEquity": _r(0.15),   # ROA absent -> ROCE falls back to ROE
    })
    f = YahooFundamentals(client=FakeHttp(FakeResponse(payload))).get_fundamentals(RELIANCE)
    assert f.roce_pct == 15.0
    assert f.operating_margin_pct == 0.0
    assert f.earnings_growth_pct == 0.0
