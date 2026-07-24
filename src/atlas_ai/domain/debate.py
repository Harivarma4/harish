"""Structured bull/bear/judge debate that precedes every recommendation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DebateArgument:
    """One side's case, expressed as a stance and its supporting points."""

    stance: str  # "BULL" | "BEAR"
    thesis: str
    points: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DebateOutcome:
    """The judge's reconciliation of the bull and bear cases.

    ``leaning`` is in [-1, 1]: negative favours the bear, positive the bull.
    """

    bull: DebateArgument
    bear: DebateArgument
    verdict: str
    leaning: float

    def __post_init__(self) -> None:
        if not -1.0 <= self.leaning <= 1.0:
            raise ValueError("leaning must be in [-1, 1]")
