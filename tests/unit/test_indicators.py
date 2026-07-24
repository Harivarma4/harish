"""Technical-indicator correctness."""

from __future__ import annotations

from atlas_ai.application.agents.indicators import atr, ema, macd, rsi, sma
from tests.conftest import make_candles


def test_sma_basic() -> None:
    assert sma([1, 2, 3, 4, 5], 5) == 3.0
    assert sma([1, 2, 3], 5) is None


def test_ema_reacts_faster_than_sma_to_a_step_up() -> None:
    # Flat, then a step up: the EMA weights recent values, so it leads the SMA.
    closes = [10.0] * 20 + [20.0] * 5
    e = ema(closes, 10)
    s = sma(closes, 10)
    assert e is not None and s is not None
    assert e > s


def test_rsi_all_gains_is_100() -> None:
    closes = [float(i) for i in range(1, 40)]
    r = rsi(closes)
    assert r is not None
    assert round(r, 2) == 100.0


def test_rsi_all_losses_is_low() -> None:
    closes = [float(i) for i in range(40, 1, -1)]
    r = rsi(closes)
    assert r is not None
    assert r < 1.0


def test_macd_positive_histogram_in_accelerating_uptrend() -> None:
    # Accelerating (convex) uptrend: the MACD line leads its signal line.
    closes = [float(i * i) for i in range(1, 60)]
    result = macd(closes)
    assert result is not None
    _, _, hist = result
    assert hist > 0


def test_atr_positive() -> None:
    candles = make_candles([100 + (i % 5) for i in range(30)])
    a = atr(candles)
    assert a is not None
    assert a > 0
