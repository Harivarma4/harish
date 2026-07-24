"""News port — sentiment-scored news items linked to an instrument.

Not yet consumed by the working slice (the news agent is on the roadmap), but the
port is defined so the pipeline can grow into it without a redesign.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable

from atlas_ai.domain.market import Instrument


@dataclass(frozen=True, slots=True)
class NewsItem:
    """A single, summarized, sentiment-scored news article."""

    headline: str
    summary: str
    source: str
    source_reliability: float
    sentiment: float  # [-1, 1]
    published_at: datetime
    url: str | None = None


@runtime_checkable
class NewsPort(Protocol):
    def get_recent(self, instrument: Instrument, *, limit: int = 20) -> list[NewsItem]: ...
