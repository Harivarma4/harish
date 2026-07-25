"""Quant / factor agent — classic equity factors from price + fundamentals.

Computes momentum, quality, low-volatility, mean-reversion, and value factors
purely from the candles and fundamentals already in the context — no extra data
feed. Each factor maps to a bull/bear signal; the blend is the factor score.
"""

from __future__ import annotations

import numpy as np

from atlas_ai.application.agents.base import AgentContext
from atlas_ai.application.agents.indicators import sma
from atlas_ai.domain.analysis import AgentReport, Signal
from atlas_ai.domain.enums import AgentKind, SignalStrength
from atlas_ai.domain.market import Fundamentals
from atlas_ai.domain.value_objects import Score

_SCALE = (
    SignalStrength.STRONG_BEARISH,
    SignalStrength.BEARISH,
    SignalStrength.NEUTRAL,
    SignalStrength.BULLISH,
    SignalStrength.STRONG_BULLISH,
)


def _grade(value: float, thresholds: tuple[float, float, float, float]) -> SignalStrength:
    """Map a value to a signal using ascending thresholds (higher = bullish)."""
    t0, t1, t2, t3 = thresholds
    rank = 0 if value < t0 else 1 if value < t1 else 2 if value < t2 else 3 if value < t3 else 4
    return _SCALE[rank]


class QuantAgent:
    """Scores an instrument on classic factors."""

    kind = AgentKind.QUANT

    def analyze(self, ctx: AgentContext) -> AgentReport:
        closes = [c.close for c in ctx.candles]
        signals = [
            self._momentum(closes),
            self._low_volatility(closes),
            self._mean_reversion(closes),
            self._quality(ctx.fundamentals),
            self._value(ctx.fundamentals),
        ]
        bias = sum(s.directional_score for s in signals) / len(signals)
        score = Score(round((bias + 1.0) * 50.0, 2))
        rationale = "Factors — " + "; ".join(
            f"{s.name} {s.strength.value.split('_')[-1].lower()}" for s in signals
        )
        return AgentReport(
            agent=self.kind,
            score=score,
            signals=tuple(signals),
            rationale=rationale + ".",
            assumptions=(
                "Factor premia (momentum, quality, low-vol, value) persist on average.",
                "Price history is clean and split/dividend-adjusted.",
            ),
            risks=(
                "Factors can underperform for extended stretches and reverse sharply.",
                "Crowded factors are prone to sudden unwinds.",
            ),
        )

    def _momentum(self, closes: list[float]) -> Signal:
        # Trailing return over ~6 months (or the full window if shorter).
        if len(closes) < 2:
            return Signal("Momentum", SignalStrength.NEUTRAL, "Trailing return", 0.0)
        lookback = min(126, len(closes) - 1)
        ret = (closes[-1] - closes[-1 - lookback]) / closes[-1 - lookback] * 100.0
        return Signal(
            "Momentum", _grade(ret, (-15.0, -5.0, 5.0, 15.0)),
            "Trailing price return, %", round(ret, 2),
        )

    def _low_volatility(self, closes: list[float]) -> Signal:
        # Lower realized volatility scores higher (low-vol anomaly).
        if len(closes) < 3:
            return Signal("LowVol", SignalStrength.NEUTRAL, "Realized volatility", 0.0)
        arr = np.array(closes, dtype=float)
        daily = np.diff(arr) / arr[:-1]
        ann_vol = float(np.std(daily, ddof=1)) * (252 ** 0.5) * 100.0
        # Negate so that low volatility maps to the bullish end.
        return Signal(
            "LowVol", _grade(-ann_vol, (-45.0, -30.0, -20.0, -12.0)),
            "Annualized volatility (lower is better), %", round(ann_vol, 2),
        )

    def _mean_reversion(self, closes: list[float]) -> Signal:
        # Distance below a 50-day SMA is constructive (oversold); far above is not.
        base = sma(closes, min(50, len(closes)))
        if base is None or base == 0:
            return Signal("MeanReversion", SignalStrength.NEUTRAL, "Extension vs SMA", 0.0)
        extension = (closes[-1] - base) / base * 100.0
        # Negate: below the average (negative extension) → bullish reversion.
        return Signal(
            "MeanReversion", _grade(-extension, (-15.0, -7.0, 7.0, 15.0)),
            "Price extension vs 50-SMA, % (below = oversold)", round(extension, 2),
        )

    def _quality(self, f: Fundamentals) -> Signal:
        # Composite of ROE, leverage, and net margin, normalized to a 0..100 score.
        roe = min(max(f.roe_pct, 0.0), 40.0) / 40.0
        leverage = 1.0 - min(f.debt_to_equity, 2.0) / 2.0
        margin = min(max(f.net_margin_pct, 0.0), 25.0) / 25.0
        quality = (roe + leverage + margin) / 3.0 * 100.0
        return Signal(
            "Quality", _grade(quality, (35.0, 50.0, 62.0, 75.0)),
            "ROE / low-leverage / margin composite (0-100)", round(quality, 1),
        )

    def _value(self, f: Fundamentals) -> Signal:
        # Cheaper (lower P/E and P/B) scores higher. Blend an inverse of each.
        pe_score = max(0.0, 1.0 - min(f.pe, 60.0) / 60.0)
        pb_score = max(0.0, 1.0 - min(f.pb, 12.0) / 12.0)
        value = (pe_score + pb_score) / 2.0 * 100.0
        return Signal(
            "Value", _grade(value, (30.0, 45.0, 58.0, 72.0)),
            "Cheapness from P/E and P/B (0-100)", round(value, 1),
        )
