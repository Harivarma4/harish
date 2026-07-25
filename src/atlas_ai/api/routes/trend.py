"""Weekly-trend endpoint — a factual read of recent price action."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from atlas_ai.api.container import Container
from atlas_ai.api.dependencies import get_container
from atlas_ai.api.schemas import TrendResponse, to_trend_response
from atlas_ai.application.use_cases.get_weekly_trend import GetWeeklyTrendCommand
from atlas_ai.domain.enums import Exchange

router = APIRouter(prefix="/api/v1/trend", tags=["trend"])


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
