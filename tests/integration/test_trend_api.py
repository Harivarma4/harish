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


def test_indices_all(client: TestClient) -> None:
    resp = client.get("/api/v1/trend/indices")
    assert resp.status_code == 200
    body = resp.json()
    assert body["group"] == "all"
    keys = {i["key"] for i in body["indices"]}
    assert {"nifty50", "banknifty", "sensex", "niftyit"} <= keys
    for idx in body["indices"]:
        assert idx["direction"] in {"UP", "DOWN", "FLAT"}
        assert idx["symbol"].startswith("^")
    assert body["disclaimer"]


def test_indices_group_filter(client: TestClient) -> None:
    broad = client.get("/api/v1/trend/indices", params={"group": "broad"}).json()
    assert {i["key"] for i in broad["indices"]} == {"nifty50", "banknifty", "sensex"}


def test_indices_rejects_bad_group(client: TestClient) -> None:
    assert client.get("/api/v1/trend/indices", params={"group": "bogus"}).status_code == 422


def test_single_symbol_route_still_works(client: TestClient) -> None:
    # "/indices" must not shadow the "/{symbol}" route for real symbols.
    assert client.get("/api/v1/trend/RELIANCE").status_code == 200
