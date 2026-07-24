"""Recommendation endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from atlas_ai.api.container import Container
from atlas_ai.api.dependencies import get_container
from atlas_ai.api.schemas import (
    RecommendationRequest,
    RecommendationResponse,
    to_response,
)
from atlas_ai.application.use_cases.generate_recommendation import (
    GenerateRecommendationCommand,
)

router = APIRouter(prefix="/api/v1/recommendations", tags=["recommendations"])


@router.post("", response_model=RecommendationResponse, status_code=status.HTTP_201_CREATED)
def create_recommendation(
    body: RecommendationRequest, container: Container = Depends(get_container)
) -> RecommendationResponse:
    """Run the multi-agent research pipeline and return a full recommendation."""
    use_case = container.generate_recommendation()
    command = GenerateRecommendationCommand(
        symbol=body.symbol,
        exchange=body.exchange,
        capital=body.capital,
        time_horizon=body.time_horizon,
    )
    recommendation = use_case.execute(command)
    return to_response(recommendation)


@router.get("/{recommendation_id}", response_model=RecommendationResponse)
def get_recommendation(
    recommendation_id: str, container: Container = Depends(get_container)
) -> RecommendationResponse:
    recommendation = container.repository.get(recommendation_id)
    if recommendation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recommendation {recommendation_id} not found",
        )
    return to_response(recommendation)
