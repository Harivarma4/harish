"""Behavioral-finance agent — market psychology from price + volume.

Reads crowd behaviour (fear/greed, volatility regime, volume herding) from the
candles already in context — no new feed. Behavioral signals are largely
*contrarian*: euphoric extension is a caution, capitulation is an opportunity.
"""

from __future__ import annotations

import numpy as np

from atlas_ai.application.agents.base import AgentContext
from atlas_ai.application.agents.indicators import atr, rsi, sma
from atlas_ai.domain.analysis import AgentReport, Signal
from atlas_ai.domain.enums import AgentKind, SignalStrength
from atlas_ai.domain.market import Candle
from atlas_ai.domain.value_objects import Score

_SCALE = (
    SignalStrength.STRONG_BEARISH,
    SignalStrength.BEARISH,
    SignalStrength.NEUTRAL,
    SignalStrength.BULLISH,
    SignalStrength.STRONG_BULLISH,
)


def _grade(
    value: float, thresholds: tuple[float, float, float, float], *, higher_is_better: bool
) -> SignalStrength:
    t0, t1, t2, t3 = thresholds
    rank = 0 if value < t0 else 1 if value < t1 else 2 if value < t2 else 3 if value < t3 else 4
    scale = _SCALE if higher_is_better else _SCALE[::-1]
    return scale[rank]


class BehavioralAgent:
    """Scores market psychology; contrarian at the extremes."""

    kind = AgentKind.BEHAVIORAL

    def analyze(self, ctx: AgentContext) -> AgentReport:
        candles = ctx.candles
        closes = [c.close for c in candles]
        signals = [
            self._fear_greed(closes),
            self._volatility_regime(candles),
            self._volume_herding(candles),
        ]
        bias = sum(s.directional_score for s in signals) / len(signals)
        score = Score(round((bias + 1.0) * 50.0, 2))
        rationale = "Crowd psychology — " + "; ".join(
            f"{s.name} {s.strength.value.split('_')[-1].lower()}" for s in signals
        )
        return AgentReport(
            agent=self.kind,
            score=score,
            signals=tuple(signals),
            rationale=rationale + ".",
            assumptions=(
                "Extreme sentiment mean-reverts; the crowd overshoots at extremes.",
                "Volume and volatility reflect participation and emotion.",
            ),
            risks=(
                "Trends can stay irrational longer than expected; contrarian timing is hard.",
                "A regime change can invalidate the mean-reversion assumption.",
            ),
        )

    def _fear_greed(self, closes: list[float]) -> Signal:
        # Greed index (0-100) from RSI + extension vs the 50-SMA. High greed is a
        # contrarian caution; deep fear is a contrarian opportunity.
        r = rsi(closes) if len(closes) > 14 else 50.0
        base = sma(closes, min(50, len(closes)))
        extension = ((closes[-1] - base) / base * 100.0) if base else 0.0
        greed = 0.5 * (r or 50.0) + 0.5 * (50.0 + max(-25.0, min(25.0, extension)))
        greed = max(0.0, min(100.0, greed))
        return Signal(
            "FearGreed", _grade(greed, (25.0, 40.0, 60.0, 75.0), higher_is_better=False),
            "Greed index 0-100 (high = euphoric, contrarian)", round(greed, 1),
        )

    def _volatility_regime(self, candles: list[Candle]) -> Signal:
        # Rising volatility vs its baseline is risk-off (fear).
        short = atr(candles, 14)
        long = atr(candles, 60) if len(candles) > 60 else short
        if not short or not long:
            return Signal("VolRegime", SignalStrength.NEUTRAL, "Volatility regime", 1.0)
        ratio = short / long
        return Signal(
            "VolRegime", _grade(ratio, (0.8, 1.0, 1.2, 1.4), higher_is_better=False),
            "Recent vs baseline volatility (rising = risk-off)", round(ratio, 2),
        )

    def _volume_herding(self, candles: list[Candle]) -> Signal:
        # A volume surge into a rally is herding (caution); a surge into a
        # sell-off is capitulation (opportunity).
        if len(candles) < 30:
            return Signal("VolumeHerding", SignalStrength.NEUTRAL, "Volume vs baseline", 1.0)
        vols = np.array([c.volume for c in candles], dtype=float)
        recent = float(np.mean(vols[-5:]))
        baseline = float(np.mean(vols[-30:]))
        ratio = recent / baseline if baseline else 1.0
        recent_ret = (candles[-1].close - candles[-6].close) / candles[-6].close
        if ratio > 1.5 and recent_ret > 0.01:
            strength = SignalStrength.BEARISH        # herding into strength
        elif ratio > 1.5 and recent_ret < -0.01:
            strength = SignalStrength.BULLISH        # capitulation
        else:
            strength = SignalStrength.NEUTRAL
        return Signal(
            "VolumeHerding", strength, "Volume surge vs price direction", round(ratio, 2),
        )
