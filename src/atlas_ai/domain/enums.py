"""Enumerations used across the domain."""

from __future__ import annotations

from enum import StrEnum


class Exchange(StrEnum):
    """Supported Indian exchanges."""

    NSE = "NSE"
    BSE = "BSE"


class Action(StrEnum):
    """The directional call of a recommendation."""

    BUY = "BUY"
    ACCUMULATE = "ACCUMULATE"
    HOLD = "HOLD"
    REDUCE = "REDUCE"
    SELL = "SELL"
    AVOID = "AVOID"


class Conviction(StrEnum):
    """Qualitative strength of a recommendation, derived from confidence."""

    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"

    @classmethod
    def from_confidence(cls, confidence: float) -> Conviction:
        if confidence >= 0.66:
            return cls.HIGH
        if confidence >= 0.4:
            return cls.MODERATE
        return cls.LOW


class TimeHorizon(StrEnum):
    """Intended holding horizon for a thesis."""

    INTRADAY = "INTRADAY"
    SHORT_TERM = "SHORT_TERM"      # days to weeks
    MEDIUM_TERM = "MEDIUM_TERM"    # weeks to months
    LONG_TERM = "LONG_TERM"        # 1y+


class SignalStrength(StrEnum):
    """Direction/strength of an individual analytical signal."""

    STRONG_BEARISH = "STRONG_BEARISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"
    BULLISH = "BULLISH"
    STRONG_BULLISH = "STRONG_BULLISH"


class AgentKind(StrEnum):
    """Identifies which specialist produced a report."""

    FUNDAMENTAL = "FUNDAMENTAL"
    TECHNICAL = "TECHNICAL"
    RISK = "RISK"
    DEBATE = "DEBATE"
    EVIDENCE = "EVIDENCE"
