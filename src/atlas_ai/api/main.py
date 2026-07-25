"""FastAPI application factory for Project Atlas AI."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from atlas_ai import __version__
from atlas_ai.api.container import Container
from atlas_ai.api.routes import health, recommendations, status, trend
from atlas_ai.domain.recommendation import DISCLAIMER

_STATIC_DIR = Path(__file__).parent / "static"


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

    @app.get("/api", tags=["meta"])
    def meta() -> dict[str, str]:
        return {
            "name": container.settings.app_name,
            "version": __version__,
            "adapter_mode": container.settings.adapter_mode.value,
            "disclaimer": DISCLAIMER,
            "docs": "/docs",
        }

    # The dashboard (static SPA) is served at the root. Mounted last so the API
    # routers, /docs, and /openapi.json take precedence; everything else falls
    # through to the static files, with index.html at "/".
    app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="dashboard")

    return app


app = create_app()
