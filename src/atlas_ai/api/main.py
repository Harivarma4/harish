"""FastAPI application factory for Project Atlas AI."""

from __future__ import annotations

from fastapi import FastAPI

from atlas_ai import __version__
from atlas_ai.api.container import Container
from atlas_ai.api.routes import health, recommendations, status, trend
from atlas_ai.domain.recommendation import DISCLAIMER


def create_app(container: Container | None = None) -> FastAPI:
    container = container or Container()
    app = FastAPI(
        title=container.settings.app_name,
        version=__version__,
        description=(
            "Institutional AI investment-research platform for Indian markets. "
            "Research only — not investment advice. " + DISCLAIMER
        ),
    )
    app.state.container = container

    app.include_router(health.router)
    app.include_router(recommendations.router)
    app.include_router(trend.router)
    app.include_router(status.router)

    @app.get("/", tags=["meta"])
    def root() -> dict[str, str]:
        return {
            "name": container.settings.app_name,
            "version": __version__,
            "adapter_mode": container.settings.adapter_mode.value,
            "disclaimer": DISCLAIMER,
            "docs": "/docs",
        }

    return app


app = create_app()
