"""Multi-index trend use case: aggregation, group filtering, error isolation."""

from __future__ import annotations

from datetime import date, timedelta

from atlas_ai.application.reference.indices import IndexGroup, indices_for
from atlas_ai.application.use_cases.get_index_trends import (
    GetIndexTrends,
    GetIndexTrendsCommand,
)
from atlas_ai.application.use_cases.get_weekly_trend import GetWeeklyTrend
from atlas_ai.domain.market import Candle, Instrument


class FakeMarketData:
    """Returns a rising series for every symbol, or raises for `fail_symbol`."""

    def __init__(self, *, fail_symbol: str | None = None) -> None:
        self._fail = fail_symbol

    def get_candles(self, instrument: Instrument, *, days: int) -> list[Candle]:
        if self._fail is not None and instrument.symbol == self._fail:
            raise RuntimeError(f"Yahoo returned no data for {instrument.symbol}")
        start = date(2026, 7, 17)
        return [
            Candle(on=start + timedelta(days=i), open=100.0 + i, high=105.0 + i,
                   low=95.0 + i, close=100.0 + i, volume=1_000_000)
            for i in range(days)
        ]

    def get_quote(self, instrument: Instrument):  # pragma: no cover - unused
        raise NotImplementedError


def _use_case(**kw: object) -> GetIndexTrends:
    return GetIndexTrends(weekly=GetWeeklyTrend(market_data=FakeMarketData(**kw)))


def test_all_group_returns_every_index() -> None:
    result = _use_case().execute(GetIndexTrendsCommand(group=IndexGroup.ALL))
    assert len(result.trends) == len(indices_for(IndexGroup.ALL))
    assert not result.errors
    assert all(t.summary.direction == "UP" for t in result.trends)
    assert {t.ref.key for t in result.trends} >= {"nifty50", "banknifty", "niftyit"}


def test_group_filtering() -> None:
    broad = _use_case().execute(GetIndexTrendsCommand(group=IndexGroup.BROAD))
    sector = _use_case().execute(GetIndexTrendsCommand(group=IndexGroup.SECTOR))
    assert len(broad.trends) == len(indices_for(IndexGroup.BROAD))
    assert len(sector.trends) == len(indices_for(IndexGroup.SECTOR))
    assert all(t.ref.group == "broad" for t in broad.trends)
    assert all(t.ref.group == "sector" for t in sector.trends)


def test_per_index_failure_is_isolated() -> None:
    result = _use_case(fail_symbol="^NSEBANK").execute(
        GetIndexTrendsCommand(group=IndexGroup.BROAD)
    )
    assert any(e.ref.key == "banknifty" for e in result.errors)
    assert all(t.ref.key != "banknifty" for t in result.trends)
    # the rest still succeed
    assert len(result.trends) == len(indices_for(IndexGroup.BROAD)) - 1
