"""Persistence ports — recommendation storage and an immutable audit trail."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable

from atlas_ai.domain.recommendation import Recommendation


@runtime_checkable
class RecommendationRepository(Protocol):
    """Stores and retrieves recommendations by id."""

    def save(self, recommendation: Recommendation) -> None: ...

    def get(self, recommendation_id: str) -> Recommendation | None: ...

    def list_recent(self, *, limit: int = 50) -> list[Recommendation]: ...


@dataclass(frozen=True, slots=True)
class AuditRecord:
    """An append-only audit-trail entry."""

    recommendation_id: str
    action: str
    instrument_key: str
    confidence: float
    model_version: str
    prompt_version: str
    pipeline_version: str
    reasoning_summary: str
    created_at: datetime


@runtime_checkable
class AuditRepository(Protocol):
    """Append-only store of audit records (never updated or deleted)."""

    def append(self, record: AuditRecord) -> None: ...

    def for_recommendation(self, recommendation_id: str) -> list[AuditRecord]: ...
