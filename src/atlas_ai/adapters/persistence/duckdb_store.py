"""Embedded DuckDB persistence for recommendations and the audit trail.

DuckDB gives durable, file-based storage with **no server** — a single file (or
``:memory:``) holds everything — which makes it the zero-infrastructure default.
Like the Postgres adapter it stores the rich ``Recommendation`` aggregate as JSON
(via the shared serializer) plus a small queryable projection; the audit trail is
append-only.

The DuckDB connection is wrapped in a tiny, lock-guarded handle behind a minimal
protocol and ``duckdb`` is imported lazily, so the repositories are exercised in
tests against a real in-memory database with no files and no server.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Sequence
from typing import Any, Protocol, runtime_checkable

from atlas_ai.adapters.persistence.serialization import (
    audit_from_dict,
    audit_to_dict,
    recommendation_from_dict,
    recommendation_to_dict,
)
from atlas_ai.application.ports.repositories import AuditRecord
from atlas_ai.domain.recommendation import Recommendation


class DuckDbError(RuntimeError):
    """Raised for adapter-level persistence failures."""


@runtime_checkable
class DuckDbConnection(Protocol):
    """The subset of ``duckdb.DuckDBPyConnection`` this adapter uses."""

    def execute(self, query: str, parameters: object = ...) -> Any: ...


class DuckDb:
    """A lock-guarded DuckDB connection (writes and reads are serialized).

    A single DuckDB connection is not safe for concurrent use; the lock keeps the
    repositories correct under a threaded server without a connection pool.
    """

    def __init__(self, connection: DuckDbConnection) -> None:
        self._con = connection
        self._lock = threading.Lock()

    def run(self, query: str, params: Sequence[Any] = ()) -> None:
        with self._lock:
            self._con.execute(query, list(params))

    def query(self, query: str, params: Sequence[Any] = ()) -> list[tuple[Any, ...]]:
        with self._lock:
            return list(self._con.execute(query, list(params)).fetchall())


def open_duckdb(path: str) -> DuckDb:
    """Open (or create) a DuckDB database at ``path`` (or ``:memory:``)."""
    try:
        import duckdb
    except ImportError as exc:  # pragma: no cover - only without the extra
        raise DuckDbError(
            "The 'duckdb' package is required for DuckDB persistence. "
            "Install it with: pip install 'atlas-ai[duckdb]'"
        ) from exc
    return DuckDb(duckdb.connect(path))


_SCHEMA = (
    "CREATE SEQUENCE IF NOT EXISTS atlas_audit_seq START 1",
    """
    CREATE TABLE IF NOT EXISTS recommendations (
        id          VARCHAR PRIMARY KEY,
        symbol      VARCHAR NOT NULL,
        exchange    VARCHAR NOT NULL,
        action      VARCHAR NOT NULL,
        confidence  DOUBLE NOT NULL,
        created_at  VARCHAR NOT NULL,
        payload     VARCHAR NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_records (
        seq               BIGINT PRIMARY KEY DEFAULT nextval('atlas_audit_seq'),
        recommendation_id VARCHAR NOT NULL,
        created_at        VARCHAR NOT NULL,
        payload           VARCHAR NOT NULL
    )
    """,
)


def create_schema(db: DuckDb) -> None:
    """Create the tables/sequence if absent."""
    for statement in _SCHEMA:
        db.run(statement)


class DuckDbRecommendationRepository:
    """Durable ``RecommendationRepository`` backed by an embedded DuckDB file."""

    def __init__(self, db: DuckDb) -> None:
        self._db = db

    def save(self, recommendation: Recommendation) -> None:
        payload = json.dumps(recommendation_to_dict(recommendation))
        try:
            self._db.run(
                """
                INSERT INTO recommendations
                    (id, symbol, exchange, action, confidence, created_at, payload)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (id) DO UPDATE SET
                    symbol = excluded.symbol,
                    exchange = excluded.exchange,
                    action = excluded.action,
                    confidence = excluded.confidence,
                    created_at = excluded.created_at,
                    payload = excluded.payload
                """,
                (
                    recommendation.id,
                    recommendation.instrument.symbol,
                    recommendation.instrument.exchange.value,
                    recommendation.action.value,
                    recommendation.confidence.value,
                    recommendation.governance.generated_at.isoformat(),
                    payload,
                ),
            )
        except Exception as exc:  # noqa: BLE001 - surface driver/DB errors uniformly
            raise DuckDbError(
                f"Failed to save recommendation {recommendation.id}: {exc}"
            ) from exc

    def get(self, recommendation_id: str) -> Recommendation | None:
        rows = self._db.query(
            "SELECT payload FROM recommendations WHERE id = ?", (recommendation_id,)
        )
        if not rows:
            return None
        return recommendation_from_dict(json.loads(rows[0][0]))

    def list_recent(self, *, limit: int = 50) -> list[Recommendation]:
        rows = self._db.query(
            "SELECT payload FROM recommendations ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        return [recommendation_from_dict(json.loads(r[0])) for r in rows]


class DuckDbAuditRepository:
    """Append-only ``AuditRepository`` backed by an embedded DuckDB file."""

    def __init__(self, db: DuckDb) -> None:
        self._db = db

    def append(self, record: AuditRecord) -> None:
        payload = json.dumps(audit_to_dict(record))
        try:
            self._db.run(
                "INSERT INTO audit_records (recommendation_id, created_at, payload) "
                "VALUES (?, ?, ?)",
                (record.recommendation_id, record.created_at.isoformat(), payload),
            )
        except Exception as exc:  # noqa: BLE001
            raise DuckDbError(f"Failed to append audit record: {exc}") from exc

    def for_recommendation(self, recommendation_id: str) -> list[AuditRecord]:
        rows = self._db.query(
            "SELECT payload FROM audit_records WHERE recommendation_id = ? "
            "ORDER BY seq ASC",
            (recommendation_id,),
        )
        return [audit_from_dict(json.loads(r[0])) for r in rows]

    def all(self) -> list[AuditRecord]:
        rows = self._db.query("SELECT payload FROM audit_records ORDER BY seq ASC")
        return [audit_from_dict(json.loads(r[0])) for r in rows]
