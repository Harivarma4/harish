"""Evidence and provenance for explainable recommendations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class Source:
    """Provenance for a piece of evidence, with a reliability score in [0, 1]."""

    name: str
    reliability: float
    url: str | None = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.reliability <= 1.0:
            raise ValueError(
                f"Source reliability must be in [0, 1], got {self.reliability!r}"
            )


@dataclass(frozen=True, slots=True)
class Evidence:
    """A single, attributable claim supporting or opposing a thesis.

    ``weight`` reflects how strongly this evidence bears on the thesis; a
    negative weight denotes counter-evidence.
    """

    claim: str
    source: Source
    weight: float = 1.0
    observed_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )

    @property
    def is_counter(self) -> bool:
        return self.weight < 0
