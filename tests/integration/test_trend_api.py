"""Weekly-trend API endpoint (mock market data via TestClient)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from atlas_ai.api.main import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_weekly_trend_ok(client: TestClient) -> None:
    resp = client.get("/api/v1/trend/RELIANCE", params={"exchange": "NSE", "sessions": 5})
    assert resp.status_code == 200
    body = resp.json()
    assert body["symbol"] == "RELIANCE"
    assert body["exchange"] == "NSE"
    assert body["sessions_count"] == 5
    assert body["direction"] in {"UP", "DOWN", "FLAT"}
    assert body["week_high"] >= body["week_low"]
    assert len(body["sessions"]) == 5
    assert body["disclaimer"]


def test_weekly_trend_default_sessions(client: TestClient) -> None:
    body = client.get("/api/v1/trend/TCS").json()
    assert body["sessions_count"] == 5  # default ~1 week


def test_weekly_trend_rejects_bad_session_count(client: TestClient) -> None:
    assert client.get("/api/v1/trend/RELIANCE", params={"sessions": 0}).status_code == 422
    assert client.get("/api/v1/trend/RELIANCE", params={"sessions": 999}).status_code == 422
