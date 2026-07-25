"""Status endpoint — the orchestrator's whole-system view of the agent fleet."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from atlas_ai.api.container import Container
from atlas_ai.api.dependencies import get_container
from atlas_ai.api.schemas import SystemStatusResponse, to_status_response

router = APIRouter(prefix="/api/v1", tags=["status"])


@router.get("/status", response_model=SystemStatusResponse)
def system_status(
    container: Container = Depends(get_container),
) -> SystemStatusResponse:
    """Report every agent's role, responsibilities, data basis, and blend weight.

    The orchestration layer (CEO mandate / COO operations / CTO readiness)
    summarises which agents are live and on what data — real vs mock — so the
    authenticity of each contribution is explicit.
    """
    return to_status_response(container.orchestrator.status())
