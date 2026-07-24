"""In-memory persistence adapters for recommendations and the audit trail.

Suitable for the foundation build and tests. A Postgres/TimescaleDB-backed
implementation of the same ports lands in a later phase.
"""

from __future__ import annotations

from atlas_ai.application.ports.repositories import AuditRecord
from atlas_ai.domain.recommendation import Recommendation


class InMemoryRecommendationRepository:
    """Satisfies ``RecommendationRepository``."""

    def __init__(self) -> None:
        self._store: dict[str, Recommendation] = {}
        self._order: list[str] = []

    def save(self, recommendation: Recommendation) -> None:
        if recommendation.id not in self._store:
            self._order.append(recommendation.id)
        self._store[recommendation.id] = recommendation

    def get(self, recommendation_id: str) -> Recommendation | None:
        return self._store.get(recommendation_id)

    def list_recent(self, *, limit: int = 50) -> list[Recommendation]:
        ids = self._order[-limit:][::-1]
        return [self._store[i] for i in ids]


class InMemoryAuditRepository:
    """Append-only audit store. Records are never mutated or removed."""

    def __init__(self) -> None:
        self._records: list[AuditRecord] = []

    def append(self, record: AuditRecord) -> None:
        self._records.append(record)

    def for_recommendation(self, recommendation_id: str) -> list[AuditRecord]:
        return [r for r in self._records if r.recommendation_id == recommendation_id]

    def all(self) -> list[AuditRecord]:
        return list(self._records)
