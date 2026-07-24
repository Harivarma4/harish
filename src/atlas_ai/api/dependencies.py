"""FastAPI dependency providers that read from the app's composition root."""

from __future__ import annotations

from fastapi import Request

from atlas_ai.api.container import Container


def get_container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container
