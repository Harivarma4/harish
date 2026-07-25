"""DuckDB repositories exercised against a real embedded database."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import duckdb

from atlas_ai.adapters.persistence.duckdb_store import (
    DuckDb,
    DuckDbAuditRepository,
    DuckDbRecommendationRepository,
    create_schema,
    open_duckdb,
)
from atlas_ai.api.container import Container
from atlas_ai.application.ports.repositories import AuditRecord
from atlas_ai.application.use_cases.generate_recommendation import (
    GenerateRecommendationCommand,
)
from atlas_ai.domain.enums import Exchange
from atlas_ai.domain.recommendation import Recommendation
from tests.conftest import mock_settings


def _memory_db() -> DuckDb:
    db = DuckDb(duckdb.connect(":memory:"))
    create_schema(db)
    return db


def _a_recommendation() -> Recommendation:
    return Container(mock_settings()).generate_recommendation().execute(
        GenerateRecommendationCommand(symbol="RELIANCE", exchange=Exchange.NSE, capital=100_000)
    )


def test_save_then_get_round_trips() -> None:
    repo = DuckDbRecommendationRepository(_memory_db())
    rec = _a_recommendation()
    repo.save(rec)
    assert repo.get(rec.id) == rec
    assert repo.get("missing") is None


def test_save_is_idempotent_upsert() -> None:
    db = _memory_db()
    repo = DuckDbRecommendationRepository(db)
    rec = _a_recommendation()
    repo.save(rec)
    repo.save(rec)
    assert len(repo.list_recent()) == 1


def test_audit_append_and_query() -> None:
    audit = DuckDbAuditRepository(_memory_db())
    record = AuditRecord(
        recommendation_id="rec-1", action="BUY", instrument_key="NSE:RELIANCE",
        confidence=0.6, model_version="m", prompt_version="v1",
        pipeline_version="p", reasoning_summary="ok",
        created_at=datetime(2026, 7, 25, tzinfo=UTC),
    )
    audit.append(record)
    audit.append(record)
    assert audit.for_recommendation("rec-1") == [record, record]
    assert audit.for_recommendation("other") == []
    assert len(audit.all()) == 2


def test_persists_to_file_across_connections(tmp_path: Path) -> None:
    # The whole point of DuckDB here: durability with no server. Write, close,
    # reopen a fresh connection to the same file, and read it back.
    path = str(tmp_path / "atlas.duckdb")
    rec = _a_recommendation()

    writer = open_duckdb(path)
    create_schema(writer)
    DuckDbRecommendationRepository(writer).save(rec)

    reader = open_duckdb(path)
    assert DuckDbRecommendationRepository(reader).get(rec.id) == rec


def test_container_uses_duckdb_when_configured(tmp_path: Path) -> None:
    from atlas_ai.adapters.config import Settings

    path = str(tmp_path / "container.duckdb")
    container = Container(
        Settings(
            adapter_mode="mock", llm_provider="mock",
            persistence_backend="duckdb", duckdb_path=path,
        )
    )
    assert isinstance(container.repository, DuckDbRecommendationRepository)
    assert container._persistence_is_durable is True
    assert container._persistence_label == "DuckDB"

    # GET-after-POST works through the durable store.
    rec = container.generate_recommendation().execute(
        GenerateRecommendationCommand(symbol="INFY", exchange=Exchange.NSE, capital=50_000)
    )
    assert container.repository.get(rec.id) is not None
    assert container.audit.for_recommendation(rec.id)
