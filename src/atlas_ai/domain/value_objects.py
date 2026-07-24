"""Immutable value objects with self-validating invariants."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Confidence:
    """A calibrated confidence in [0, 1].

    Recommendations are never certain; this type makes the uncertainty explicit
    and impossible to omit or set out of range.
    """

    value: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.value <= 1.0:
            raise ValueError(f"Confidence must be in [0, 1], got {self.value!r}")

    def as_percent(self) -> float:
        return round(self.value * 100.0, 2)

    def __float__(self) -> float:
        return self.value


@dataclass(frozen=True, slots=True)
class Score:
    """A normalized analytical score in [0, 100] (higher = more constructive)."""

    value: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.value <= 100.0:
            raise ValueError(f"Score must be in [0, 100], got {self.value!r}")

    def as_unit(self) -> float:
        """Return the score on a 0..1 scale."""
        return self.value / 100.0


@dataclass(frozen=True, slots=True)
class Money:
    """A monetary amount in a given currency (INR by default)."""

    amount: float
    currency: str = "INR"

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError(f"Money amount cannot be negative, got {self.amount!r}")

    def __str__(self) -> str:
        return f"{self.currency} {self.amount:,.2f}"


@dataclass(frozen=True, slots=True)
class Percent:
    """A percentage value (e.g. 12.5 means 12.5%)."""

    value: float

    def as_fraction(self) -> float:
        return self.value / 100.0
