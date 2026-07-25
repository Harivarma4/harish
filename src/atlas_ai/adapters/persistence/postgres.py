"""PostgreSQL-backed persistence for recommendations and the audit trail.

Durable implementations of ``RecommendationRepository`` and ``AuditRepository``.
The rich ``Recommendation`` aggregate is stored as JSONB (via the explicit
serializer) alongside a small queryable projection (symbol, action, confidence,
timestamp); the audit trail is append-only.

Design mirrors the other real adapters: the DB connection is obtained through an
injected *connection factory* behind a minimal ``DbConnection`` Protocol, and
``psycopg`` is imported lazily. That keeps all SQL/mapping logic unit-testable
offline with a fake connection — no database or driver required for the suite.
It needs a reachable Postgres and ``psycopg`` where deployed.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from typing import Any, Protocol, runtime_checkable

from atlas_ai.adapters.persistence.serialization import (
    audit_from_dict,
    audit_to_dict,
    recommendation_from_dict,
    recommendation_to_dict,
)
from atlas_ai.application.ports.repositories import AuditRecord
from atlas_ai.domain.recommendation import Recommendation


@runtime_checkable
class DbCursor(Protocol):
    def fetchone(self) -> tuple[Any, ...] | None: ...

    def fetchall(self) -> list[tuple[Any, ...]]: ...


@runtime_checkable
class DbConnection(Protocol):
    """A transactional connection used as a context manager (psycopg-shaped).

    Committing/closing on ``__exit__`` matches ``psycopg.Connection`` semantics.
    """

    def execute(self, query: str, params: Sequence[Any] = ()) -> DbCursor: ...

    def __enter__(self) -> DbConnection: ...

    def __exit__(self, *exc: object) -> bool | None: ...


ConnectionFactory = Callable[[], DbConnection]


class PostgresError(RuntimeError):
    """Raised for adapter-level persistence failures."""


def psycopg_factory(dsn: str) -> ConnectionFactory:
    """A connection factory that opens a fresh ``psycopg`` connection per call."""

    def connect() -> DbConnection:
        try:
            import psycopg  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - only without the extra
            raise PostgresError(
                "The 'psycopg' package is required for Postgres persistence. "
                "Install it with: pip install 'atlas-ai[postgres]'"
            ) from exc
        conn: DbConnection = psycopg.connect(dsn)
        return conn

    return connect


_SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS recommendations (
        id          TEXT PRIMARY KEY,
        symbol      TEXT NOT NULL,
        exchange    TEXT NOT NULL,
        action      TEXT NOT NULL,
        confidence  DOUBLE PRECISION NOT NULL,
        created_at  TIMESTAMPTZ NOT NULL,
        payload     JSONB NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_recommendations_created_at "
    "ON recommendations (created_at DESC)",
    """
    CREATE TABLE IF NOT EXISTS audit_records (
        id                BIGSERIAL PRIMARY KEY,
        recommendation_id TEXT NOT NULL,
        created_at        TIMESTAMPTZ NOT NULL,
        payload           JSONB NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_audit_recommendation_id "
    "ON audit_records (recommendation_id)",
)


def create_schema(connect: ConnectionFactory) -> None:
    """Create the tables/indexes if absent. Also validates connectivity early."""
    with connect() as conn:
        for statement in _SCHEMA:
            conn.execute(statement)


class PostgresRecommendationRepository:
    """Durable ``RecommendationRepository`` backed by Postgres/JSONB."""

    def __init__(self, connect: ConnectionFactory) -> None:
        self._connect = connect

    def save(self, recommendation: Recommendation) -> None:
        payload = json.dumps(recommendation_to_dict(recommendation))
        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO recommendations
                        (id, symbol, exchange, action, confidence, created_at, payload)
                    VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
                    ON CONFLICT (id) DO UPDATE SET
                        symbol = EXCLUDED.symbol,
                        exchange = EXCLUDED.exchange,
                        action = EXCLUDED.action,
                        confidence = EXCLUDED.confidence,
                        created_at = EXCLUDED.created_at,
                        payload = EXCLUDED.payload
                    """,
                    (
                        recommendation.id,
                        recommendation.instrument.symbol,
                        recommendation.instrument.exchange.value,
                        recommendation.action.value,
                        recommendation.confidence.value,
                        recommendation.governance.generated_at,
                        payload,
                    ),
                )
        except Exception as exc:  # noqa: BLE001 - surface driver/DB errors uniformly
            raise PostgresError(
                f"Failed to save recommendation {recommendation.id}: {exc}"
            ) from exc

    def get(self, recommendation_id: str) -> Recommendation | None:
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT payload::text FROM recommendations WHERE id = %s",
                    (recommendation_id,),
                ).fetchone()
        except Exception as exc:  # noqa: BLE001
            raise PostgresError(
                f"Failed to load recommendation {recommendation_id}: {exc}"
            ) from exc
        if row is None:
            return None
        return recommendation_from_dict(json.loads(row[0]))

    def list_recent(self, *, limit: int = 50) -> list[Recommendation]:
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT payload::text FROM recommendations "
                    "ORDER BY created_at DESC LIMIT %s",
                    (limit,),
                ).fetchall()
        except Exception as exc:  # noqa: BLE001
            raise PostgresError(f"Failed to list recommendations: {exc}") from exc
        return [recommendation_from_dict(json.loads(r[0])) for r in rows]


class PostgresAuditRepository:
    """Append-only ``AuditRepository`` backed by Postgres/JSONB."""

    def __init__(self, connect: ConnectionFactory) -> None:
        self._connect = connect

    def append(self, record: AuditRecord) -> None:
        payload = json.dumps(audit_to_dict(record))
        try:
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO audit_records (recommendation_id, created_at, payload) "
                    "VALUES (%s, %s, %s::jsonb)",
                    (record.recommendation_id, record.created_at, payload),
                )
        except Exception as exc:  # noqa: BLE001
            raise PostgresError(f"Failed to append audit record: {exc}") from exc

    def for_recommendation(self, recommendation_id: str) -> list[AuditRecord]:
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT payload::text FROM audit_records "
                    "WHERE recommendation_id = %s ORDER BY id ASC",
                    (recommendation_id,),
                ).fetchall()
        except Exception as exc:  # noqa: BLE001
            raise PostgresError(f"Failed to load audit for {recommendation_id}: {exc}") from exc
        return [audit_from_dict(json.loads(r[0])) for r in rows]

    def all(self) -> list[AuditRecord]:
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT payload::text FROM audit_records ORDER BY id ASC"
                ).fetchall()
        except Exception as exc:  # noqa: BLE001
            raise PostgresError(f"Failed to list audit records: {exc}") from exc
        return [audit_from_dict(json.loads(r[0])) for r in rows]
