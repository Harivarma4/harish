"""Black-Scholes pricing and Greeks for European options.

Real, closed-form math (no external pricing library): prices, first-order Greeks,
and an implied-volatility solver by bisection. The options agent uses these to
derive ATM Greeks and to sanity-check quoted implied volatilities. Dividends are
ignored (a documented simplification for short-dated index/equity options).
"""

from __future__ import annotations

import math

from atlas_ai.domain.options import Greeks, OptionRight

_SQRT_2PI = math.sqrt(2.0 * math.pi)


def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / _SQRT_2PI


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _d1_d2(
    spot: float, strike: float, t: float, r: float, sigma: float
) -> tuple[float, float]:
    vol = sigma * math.sqrt(t)
    d1 = (math.log(spot / strike) + (r + 0.5 * sigma * sigma) * t) / vol
    return d1, d1 - vol


def price(
    spot: float, strike: float, t: float, r: float, sigma: float, right: OptionRight
) -> float:
    """European option price. Degenerate inputs fall back to intrinsic value."""
    if spot <= 0.0 or strike <= 0.0 or t <= 0.0 or sigma <= 0.0:
        intrinsic = spot - strike if right is OptionRight.CALL else strike - spot
        return max(intrinsic, 0.0)
    d1, d2 = _d1_d2(spot, strike, t, r, sigma)
    discount = math.exp(-r * t)
    if right is OptionRight.CALL:
        return spot * _norm_cdf(d1) - strike * discount * _norm_cdf(d2)
    return strike * discount * _norm_cdf(-d2) - spot * _norm_cdf(-d1)


def greeks(
    spot: float, strike: float, t: float, r: float, sigma: float, right: OptionRight
) -> Greeks:
    """First-order Greeks (delta, gamma, vega per 1.0 vol, theta per day)."""
    if spot <= 0.0 or strike <= 0.0 or t <= 0.0 or sigma <= 0.0:
        return Greeks(delta=0.0, gamma=0.0, vega=0.0, theta=0.0)
    d1, d2 = _d1_d2(spot, strike, t, r, sigma)
    discount = math.exp(-r * t)
    pdf = _norm_pdf(d1)
    gamma = pdf / (spot * sigma * math.sqrt(t))
    vega = spot * pdf * math.sqrt(t)
    if right is OptionRight.CALL:
        delta = _norm_cdf(d1)
        theta = (
            -(spot * pdf * sigma) / (2.0 * math.sqrt(t))
            - r * strike * discount * _norm_cdf(d2)
        )
    else:
        delta = _norm_cdf(d1) - 1.0
        theta = (
            -(spot * pdf * sigma) / (2.0 * math.sqrt(t))
            + r * strike * discount * _norm_cdf(-d2)
        )
    return Greeks(
        delta=round(delta, 4),
        gamma=round(gamma, 6),
        vega=round(vega / 100.0, 4),   # per 1% vol move
        theta=round(theta / 365.0, 4),  # per calendar day
    )


def implied_volatility(
    market_price: float,
    spot: float,
    strike: float,
    t: float,
    r: float,
    right: OptionRight,
    *,
    lo: float = 1e-4,
    hi: float = 5.0,
    tol: float = 1e-4,
    max_iter: int = 100,
) -> float | None:
    """Recover implied volatility by bisection, or ``None`` if it can't bracket."""
    if market_price <= 0.0 or spot <= 0.0 or strike <= 0.0 or t <= 0.0:
        return None
    p_lo = price(spot, strike, t, r, lo, right) - market_price
    p_hi = price(spot, strike, t, r, hi, right) - market_price
    if p_lo * p_hi > 0.0:
        return None  # price not inside [lo, hi] vol bracket
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        p_mid = price(spot, strike, t, r, mid, right) - market_price
        if abs(p_mid) < tol:
            return round(mid, 4)
        if p_lo * p_mid < 0.0:
            hi = mid
        else:
            lo, p_lo = mid, p_mid
    return round(0.5 * (lo + hi), 4)
