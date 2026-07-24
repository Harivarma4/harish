"""Pure technical-indicator functions operating on candle series.

Kept dependency-free and side-effect-free so they are trivially unit-testable.
"""

from __future__ import annotations

from atlas_ai.domain.market import Candle


def sma(values: list[float], period: int) -> float | None:
    """Simple moving average of the last ``period`` values."""
    if period <= 0 or len(values) < period:
        return None
    return sum(values[-period:]) / period


def ema(values: list[float], period: int) -> float | None:
    """Exponential moving average (seeded with an SMA)."""
    if period <= 0 or len(values) < period:
        return None
    k = 2.0 / (period + 1.0)
    seed = sum(values[:period]) / period
    result = seed
    for v in values[period:]:
        result = v * k + result * (1.0 - k)
    return result


def rsi(closes: list[float], period: int = 14) -> float | None:
    """Wilder's Relative Strength Index over ``period`` closes."""
    if len(closes) <= period:
        return None
    gains = 0.0
    losses = 0.0
    for i in range(1, period + 1):
        delta = closes[i] - closes[i - 1]
        gains += max(delta, 0.0)
        losses += max(-delta, 0.0)
    avg_gain = gains / period
    avg_loss = losses / period
    for i in range(period + 1, len(closes)):
        delta = closes[i] - closes[i - 1]
        avg_gain = (avg_gain * (period - 1) + max(delta, 0.0)) / period
        avg_loss = (avg_loss * (period - 1) + max(-delta, 0.0)) / period
    if avg_loss == 0.0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def macd(
    closes: list[float], fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[float, float, float] | None:
    """Return (macd_line, signal_line, histogram), or None if insufficient data."""
    if len(closes) < slow + signal:
        return None
    macd_series: list[float] = []
    for end in range(slow, len(closes) + 1):
        window = closes[:end]
        fast_ema = ema(window, fast)
        slow_ema = ema(window, slow)
        if fast_ema is None or slow_ema is None:
            continue
        macd_series.append(fast_ema - slow_ema)
    signal_line = ema(macd_series, signal)
    if signal_line is None:
        return None
    macd_line = macd_series[-1]
    return macd_line, signal_line, macd_line - signal_line


def atr(candles: list[Candle], period: int = 14) -> float | None:
    """Average True Range over ``period`` candles."""
    if len(candles) <= period:
        return None
    true_ranges: list[float] = []
    for i in range(1, len(candles)):
        cur = candles[i]
        prev_close = candles[i - 1].close
        true_ranges.append(
            max(
                cur.high - cur.low,
                abs(cur.high - prev_close),
                abs(cur.low - prev_close),
            )
        )
    return sum(true_ranges[-period:]) / period
