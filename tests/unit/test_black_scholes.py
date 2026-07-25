"""Black-Scholes pricing and Greeks."""

from __future__ import annotations

import math

from atlas_ai.application.pricing import black_scholes as bs
from atlas_ai.domain.options import OptionRight


def test_put_call_parity() -> None:
    spot, strike, t, r, sigma = 100.0, 100.0, 0.5, 0.06, 0.25
    call = bs.price(spot, strike, t, r, sigma, OptionRight.CALL)
    put = bs.price(spot, strike, t, r, sigma, OptionRight.PUT)
    # C - P = S - K e^{-rt}
    assert math.isclose(call - put, spot - strike * math.exp(-r * t), abs_tol=1e-6)


def test_call_price_increases_with_spot() -> None:
    lo = bs.price(90.0, 100.0, 0.5, 0.06, 0.25, OptionRight.CALL)
    hi = bs.price(110.0, 100.0, 0.5, 0.06, 0.25, OptionRight.CALL)
    assert hi > lo > 0.0


def test_degenerate_inputs_return_intrinsic() -> None:
    assert bs.price(120.0, 100.0, 0.0, 0.06, 0.25, OptionRight.CALL) == 20.0
    assert bs.price(80.0, 100.0, 0.0, 0.06, 0.25, OptionRight.PUT) == 20.0
    assert bs.price(90.0, 100.0, 0.0, 0.06, 0.25, OptionRight.CALL) == 0.0


def test_delta_bounds() -> None:
    call = bs.greeks(100.0, 100.0, 0.5, 0.06, 0.25, OptionRight.CALL)
    put = bs.greeks(100.0, 100.0, 0.5, 0.06, 0.25, OptionRight.PUT)
    assert 0.0 <= call.delta <= 1.0
    assert -1.0 <= put.delta <= 0.0
    assert call.gamma > 0.0
    assert call.vega > 0.0


def test_implied_vol_recovers_input() -> None:
    spot, strike, t, r, sigma = 100.0, 105.0, 0.4, 0.06, 0.28
    px = bs.price(spot, strike, t, r, sigma, OptionRight.CALL)
    iv = bs.implied_volatility(px, spot, strike, t, r, OptionRight.CALL)
    assert iv is not None
    assert math.isclose(iv, sigma, abs_tol=1e-3)


def test_implied_vol_unbracketable_returns_none() -> None:
    # A price below intrinsic can't be matched by any positive vol.
    assert bs.implied_volatility(0.0, 100.0, 100.0, 0.4, 0.06, OptionRight.CALL) is None
