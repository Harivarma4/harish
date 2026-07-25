"""API smoke tests via FastAPI's TestClient."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from atlas_ai.api.container import Container
from atlas_ai.api.main import create_app
from tests.conftest import mock_settings


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(Container(mock_settings())))


def test_health(client: TestClient) -> None:
    assert client.get("/health/live").json() == {"status": "ok"}
    assert client.get("/health/ready").json() == {"status": "ready"}


def test_root_carries_disclaimer(client: TestClient) -> None:
    body = client.get("/").json()
    assert "disclaimer" in body
    assert body["adapter_mode"] == "mock"


def test_create_and_fetch_recommendation(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/recommendations",
        json={"symbol": "RELIANCE", "exchange": "NSE", "capital": 100000},
    )
    assert resp.status_code == 201
    body = resp.json()

    # Shape of the recommendation payload.
    assert body["symbol"] == "RELIANCE"
    assert body["action"] in {"BUY", "ACCUMULATE", "HOLD", "REDUCE", "SELL", "AVOID"}
    assert body["disclaimer"]
    assert len(body["agent_reports"]) == 8
    assert body["evidence"]
    assert body["outlook"]["simulations"] > 0
    assert "reasoning_summary" in body["governance"]

    fetched = client.get(f"/api/v1/recommendations/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == body["id"]


def test_unknown_recommendation_404(client: TestClient) -> None:
    assert client.get("/api/v1/recommendations/does-not-exist").status_code == 404


def test_invalid_capital_rejected(client: TestClient) -> None:
    resp = client.post("/api/v1/recommendations", json={"symbol": "TCS", "capital": -1})
    assert resp.status_code == 422
