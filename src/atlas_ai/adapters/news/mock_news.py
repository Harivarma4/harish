"""Deterministic, offline mock news provider.

Generates a stable set of sentiment-scored headlines per symbol (seeded by the
symbol) so the news agent runs reproducibly offline. Illustrative only — a real
adapter (Moneycontrol/ET/Reuters scraping + an NLP sentiment model) implements
the same ``NewsPort`` later.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

import numpy as np

from atlas_ai.application.ports.news import NewsItem
from atlas_ai.domain.market import Instrument

# Sources with a plausible reliability weight in [0, 1].
_SOURCES = (
    ("Reuters", 0.9),
    ("Bloomberg", 0.9),
    ("Economic Times", 0.75),
    ("Business Standard", 0.75),
    ("Moneycontrol", 0.7),
    ("Social media", 0.35),
)
_POS = ("beats estimates", "wins large order", "raises guidance", "margin expansion")
_NEG = ("misses estimates", "faces probe", "cuts guidance", "margin pressure")
_NEU = ("in focus ahead of results", "board meeting scheduled", "trades flat")


def _seed(symbol: str) -> int:
    return int(hashlib.sha256(symbol.encode()).hexdigest()[:8], 16)


class MockNews:
    """Satisfies ``NewsPort`` with deterministic synthetic, sentiment-scored news."""

    def __init__(self, *, today: datetime | None = None, count: int = 8) -> None:
        self._today = today or datetime(2026, 1, 1, tzinfo=UTC)
        self._count = count

    def get_recent(self, instrument: Instrument, *, limit: int = 20) -> list[NewsItem]:
        rng = np.random.default_rng(_seed(instrument.symbol))
        n = min(self._count, limit)
        items: list[NewsItem] = []
        for i in range(n):
            source, reliability = _SOURCES[int(rng.integers(0, len(_SOURCES)))]
            sentiment = float(round(rng.uniform(-1.0, 1.0), 2))
            if sentiment > 0.2:
                phrase = _POS[int(rng.integers(0, len(_POS)))]
            elif sentiment < -0.2:
                phrase = _NEG[int(rng.integers(0, len(_NEG)))]
            else:
                phrase = _NEU[int(rng.integers(0, len(_NEU)))]
            items.append(
                NewsItem(
                    headline=f"{instrument.symbol} {phrase}",
                    summary=f"{source} reports: {instrument.symbol} {phrase}.",
                    source=source,
                    source_reliability=reliability,
                    sentiment=sentiment,
                    published_at=self._today - timedelta(days=i),
                )
            )
        return items
