"""Postgres repositories exercised offline against a fake connection."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from atlas_ai.adapters.persistence.postgres import (
    PostgresAuditRepository,
    PostgresRecommendationRepository,
    create_schema,
)
from atlas_ai.api.container import Container
from atlas_ai.application.ports.repositories import AuditRecord
from atlas_ai.application.use_cases.generate_recommendation import (
    GenerateRecommendationCommand,
)
from atlas_ai.domain.enums import Exchange
from atlas_ai.domain.recommendation import Recommendation
from tests.conftest import mock_settings


class _FakeStore:
    """A tiny stand-in for the two tables."""

    def __init__(self) -> None:
        self.recs: dict[str, tuple[datetime, str]] = {}   # id -> (created_at, payload)
        self.audit: list[tuple[str, str]] = []            # (recommendation_id, payload)
        self.schema_statements = 0


class _FakeCursor:
    def __init__(self, rows: list[tuple[Any, ...]]) -> None:
        self._rows = rows

    def fetchone(self) -> tuple[Any, ...] | None:
        return self._rows[0] if self._rows else None

    def fetchall(self) -> list[tuple[Any, ...]]:
        return list(self._rows)


class _FakeConn:
    def __init__(self, store: _FakeStore) -> None:
        self._store = store

    def __enter__(self) -> _FakeConn:
        return self

    def __exit__(self, *exc: object) -> bool:
        return False

    def execute(self, query: str, params: tuple[Any, ...] = ()) -> _FakeCursor:
        q = " ".join(query.split())
        store = self._store
        if q.startswith("CREATE"):
            store.schema_statements += 1
            return _FakeCursor([])
        if "INSERT INTO recommendations" in q:
            rec_id, _sym, _exch, _act, _conf, created_at, payload = params
            store.recs[rec_id] = (created_at, payload)  # upsert by primary key
            return _FakeCursor([])
        if "FROM recommendations WHERE id" in q:
            row = store.recs.get(params[0])
            return _FakeCursor([(row[1],)] if row else [])
        if "FROM recommendations ORDER BY created_at DESC" in q:
            limit = params[0]
            ordered = sorted(store.recs.values(), key=lambda v: v[0], reverse=True)
            return _FakeCursor([(payload,) for _ca, payload in ordered[:limit]])
        if "INSERT INTO audit_records" in q:
            rec_id, _created_at, payload = params
            store.audit.append((rec_id, payload))
            return _FakeCursor([])
        if "FROM audit_records WHERE recommendation_id" in q:
            rid = params[0]
            return _FakeCursor([(p,) for r, p in store.audit if r == rid])
        if "FROM audit_records ORDER BY id" in q:
            return _FakeCursor([(p,) for _r, p in store.audit])
        raise AssertionError(f"Unexpected query: {q}")


def _factory(store: _FakeStore):
    def connect() -> _FakeConn:
        return _FakeConn(store)

    return connect


def _a_recommendation() -> Recommendation:
    return Container(mock_settings()).generate_recommendation().execute(
        GenerateRecommendationCommand(symbol="RELIANCE", exchange=Exchange.NSE, capital=100_000)
    )


def test_create_schema_runs_ddl() -> None:
    store = _FakeStore()
    create_schema(_factory(store))
    assert store.schema_statements >= 2  # two CREATE TABLE statements at least


def test_save_then_get_round_trips() -> None:
    store = _FakeStore()
    repo = PostgresRecommendationRepository(_factory(store))
    rec = _a_recommendation()
    repo.save(rec)
    assert repo.get(rec.id) == rec
    assert repo.get("missing") is None


def test_save_is_idempotent_upsert() -> None:
    store = _FakeStore()
    repo = PostgresRecommendationRepository(_factory(store))
    rec = _a_recommendation()
    repo.save(rec)
    repo.save(rec)
    assert len(store.recs) == 1
    assert len(repo.list_recent()) == 1


def test_list_recent_returns_saved() -> None:
    store = _FakeStore()
    repo = PostgresRecommendationRepository(_factory(store))
    rec = _a_recommendation()
    repo.save(rec)
    recent = repo.list_recent(limit=10)
    assert [r.id for r in recent] == [rec.id]


def test_audit_append_and_query() -> None:
    store = _FakeStore()
    audit = PostgresAuditRepository(_factory(store))
    record = AuditRecord(
        recommendation_id="rec-1", action="BUY", instrument_key="NSE:RELIANCE",
        confidence=0.6, model_version="m", prompt_version="v1",
        pipeline_version="p", reasoning_summary="ok",
        created_at=datetime(2026, 7, 25, tzinfo=UTC),
    )
    audit.append(record)
    assert audit.for_recommendation("rec-1") == [record]
    assert audit.for_recommendation("other") == []
    assert audit.all() == [record]
