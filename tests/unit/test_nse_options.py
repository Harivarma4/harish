"""NSE option-chain adapter parsing (offline, via a fake JSON client)."""

from __future__ import annotations

from datetime import date
from typing import Any

from atlas_ai.adapters.options.nse_options import NseOptions
from atlas_ai.domain.enums import Exchange
from atlas_ai.domain.market import Instrument

_INSTRUMENT = Instrument("RELIANCE", Exchange.NSE)


class _FakeResponse:
    def __init__(self, payload: Any, status: int = 200) -> None:
        self._payload = payload
        self.status_code = status

    def json(self) -> Any:
        return self._payload


class _FakeClient:
    def __init__(self, payload: Any, status: int = 200) -> None:
        self._payload = payload
        self._status = status
        self.warmed = False

    def warm_up(self, url: str, *, headers: dict[str, str]) -> None:
        self.warmed = True

    def get(self, url: str, *, params: dict[str, str], headers: dict[str, str]) -> _FakeResponse:
        return _FakeResponse(self._payload, self._status)


def _payload() -> dict[str, Any]:
    return {
        "records": {
            "expiryDates": ["30-Jan-2026", "27-Feb-2026"],
            "underlyingValue": 2650.0,
            "data": [
                {
                    "strikePrice": 2600,
                    "expiryDate": "30-Jan-2026",
                    "CE": {"openInterest": 12000, "impliedVolatility": 22.5,
                           "lastPrice": 80.0, "totalTradedVolume": 500,
                           "changeinOpenInterest": 300},
                    "PE": {"openInterest": 9000, "impliedVolatility": 24.0,
                           "lastPrice": 30.0, "totalTradedVolume": 400,
                           "changeinOpenInterest": -100},
                },
                {
                    "strikePrice": 2700,
                    "expiryDate": "30-Jan-2026",
                    "CE": {"openInterest": 8000, "impliedVolatility": 21.0,
                           "lastPrice": 30.0, "totalTradedVolume": 300},
                    "PE": {"openInterest": 15000, "impliedVolatility": 26.0,
                           "lastPrice": 80.0, "totalTradedVolume": 600},
                },
                {
                    "strikePrice": 2800,
                    "expiryDate": "27-Feb-2026",  # far expiry, must be filtered out
                    "CE": {"openInterest": 1, "impliedVolatility": 20.0, "lastPrice": 5.0},
                    "PE": {"openInterest": 1, "impliedVolatility": 20.0, "lastPrice": 5.0},
                },
            ],
        }
    }


def test_parses_nearest_expiry_only() -> None:
    chain = NseOptions(client=_FakeClient(_payload())).get_chain(_INSTRUMENT)
    assert chain is not None
    assert chain.spot == 2650.0
    assert chain.expiry == date(2026, 1, 30)
    # Only the two 30-Jan strikes, not the 27-Feb one.
    assert {c.strike for c in chain.calls} == {2600.0, 2700.0}
    # IV normalised from percent to fraction.
    atm = next(c for c in chain.calls if c.strike == 2600.0)
    assert abs(atm.implied_volatility - 0.225) < 1e-9


def test_warms_up_cookies_before_fetch() -> None:
    client = _FakeClient(_payload())
    NseOptions(client=client).get_chain(_INSTRUMENT)
    assert client.warmed is True


def test_non_200_returns_none() -> None:
    assert NseOptions(client=_FakeClient({}, status=403)).get_chain(_INSTRUMENT) is None


def test_malformed_payload_returns_none() -> None:
    assert NseOptions(client=_FakeClient({"nope": 1})).get_chain(_INSTRUMENT) is None
