"""Trend endpoints — factual reads of recent price action (single + multi-index)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from atlas_ai.api.container import Container
from atlas_ai.api.dependencies import get_container
from atlas_ai.api.schemas import (
    IndicesTrendResponse,
    TrendResponse,
    to_indices_response,
    to_trend_response,
)
from atlas_ai.application.reference.indices import IndexGroup
from atlas_ai.application.use_cases.get_index_trends import GetIndexTrendsCommand
from atlas_ai.application.use_cases.get_weekly_trend import GetWeeklyTrendCommand
from atlas_ai.domain.enums import Exchange

router = APIRouter(prefix="/api/v1/trend", tags=["trend"])


# Declared before "/{symbol}" so "indices" is not captured as a symbol.
@router.get("/indices", response_model=IndicesTrendResponse)
def index_trends(
    group: IndexGroup = IndexGroup.ALL,
    sessions: int = Query(default=5, ge=1, le=60, description="Number of trading sessions"),
    container: Container = Depends(get_container),
) -> IndicesTrendResponse:
    """Last-week trend for many Indian indices/sectors in one call.

    ``group`` selects ``all``, ``broad`` (Nifty 50, Bank Nifty, Sensex), or
    ``sector`` (Nifty IT, Auto, Pharma, FMCG, Metal, …). Reflects the configured
    market-data source; a failing index is reported under ``errors`` rather than
    failing the whole response. Factual history — not a prediction.
    """
    result = container.get_index_trends().execute(
        GetIndexTrendsCommand(group=group, sessions=sessions)
    )
    return to_indices_response(result)


@router.get("/{symbol}", response_model=TrendResponse)
def weekly_trend(
    symbol: str,
    exchange: Exchange = Exchange.NSE,
    sessions: int = Query(default=5, ge=1, le=60, description="Number of trading sessions"),
    container: Container = Depends(get_container),
) -> TrendResponse:
    """Return the last ``sessions`` (default ~1 week) of price action for a symbol.

    Reflects the configured market-data source (Yahoo public feed, Kite, or mock).
    Factual history for research — not a prediction.
    """
    use_case = container.get_weekly_trend()
    try:
        trend = use_case.execute(
            GetWeeklyTrendCommand(symbol=symbol, exchange=exchange, sessions=sessions)
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return to_trend_response(trend)
