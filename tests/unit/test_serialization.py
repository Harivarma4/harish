"""Round-trip serialization of the Recommendation aggregate and audit records."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from atlas_ai.adapters.persistence.serialization import (
    audit_from_dict,
    audit_to_dict,
    recommendation_from_dict,
    recommendation_to_dict,
)
from atlas_ai.api.container import Container
from atlas_ai.application.ports.repositories import AuditRecord
from atlas_ai.application.use_cases.generate_recommendation import (
    GenerateRecommendationCommand,
)
from atlas_ai.domain.enums import Exchange
from atlas_ai.domain.recommendation import Recommendation
from tests.conftest import mock_settings


@pytest.fixture
def recommendation() -> Recommendation:
    container = Container(mock_settings())
    return container.generate_recommendation().execute(
        GenerateRecommendationCommand(symbol="RELIANCE", exchange=Exchange.NSE, capital=100_000)
    )


def test_recommendation_round_trip(recommendation: Recommendation) -> None:
    restored = recommendation_from_dict(recommendation_to_dict(recommendation))
    assert restored == recommendation


def test_recommendation_round_trip_through_json(recommendation: Recommendation) -> None:
    # Exactly what the Postgres adapter does: dict -> JSON text -> dict.
    payload = json.dumps(recommendation_to_dict(recommendation))
    restored = recommendation_from_dict(json.loads(payload))
    assert restored == recommendation
    assert restored.id == recommendation.id


def test_audit_round_trip() -> None:
    record = AuditRecord(
        recommendation_id="abc-123",
        action="BUY",
        instrument_key="NSE:RELIANCE",
        confidence=0.61,
        model_version="atlas-mock-llm-v1",
        prompt_version="v1",
        pipeline_version="research-pipeline-v1",
        reasoning_summary="Balanced setup with a modest edge.",
        created_at=datetime(2026, 7, 25, 10, 30, tzinfo=UTC),
    )
    restored = audit_from_dict(json.loads(json.dumps(audit_to_dict(record))))
    assert restored == record
