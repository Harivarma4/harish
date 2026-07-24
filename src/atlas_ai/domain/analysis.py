"""Analytical primitives produced by specialist agents."""

from __future__ import annotations

from dataclasses import dataclass, field

from atlas_ai.domain.enums import AgentKind, SignalStrength
from atlas_ai.domain.value_objects import Score


@dataclass(frozen=True, slots=True)
class Signal:
    """A single named analytical observation (e.g. 'RSI', 'ROE')."""

    name: str
    strength: SignalStrength
    detail: str
    value: float | None = None

    @property
    def directional_score(self) -> float:
        """Map the qualitative strength onto [-1, 1] for aggregation."""
        return {
            SignalStrength.STRONG_BEARISH: -1.0,
            SignalStrength.BEARISH: -0.5,
            SignalStrength.NEUTRAL: 0.0,
            SignalStrength.BULLISH: 0.5,
            SignalStrength.STRONG_BULLISH: 1.0,
        }[self.strength]


@dataclass(frozen=True, slots=True)
class AgentReport:
    """The structured output of one specialist agent.

    ``score`` is a normalized 0..100 view (higher = more constructive); the
    accompanying signals and rationale make the score explainable.
    """

    agent: AgentKind
    score: Score
    signals: tuple[Signal, ...]
    rationale: str
    assumptions: tuple[str, ...] = field(default_factory=tuple)
    risks: tuple[str, ...] = field(default_factory=tuple)

    @property
    def net_bias(self) -> float:
        """Average directional bias of the report's signals in [-1, 1]."""
        if not self.signals:
            return 0.0
        return sum(s.directional_score for s in self.signals) / len(self.signals)
