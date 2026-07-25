"""Orchestration layer — the thin coordination tier over the agent pipeline.

Frames the system through three coordination roles and exposes a single, honest
status view of the whole agent fleet:

- **CEO** — the standing mandate (research, not advice; no deterministic calls).
- **COO** — operations: which agents are live and how the pipeline is wired.
- **CTO** — readiness: data authenticity per agent and any degraded surfaces.

It computes nothing predictive itself; it coordinates and reports. The status it
produces answers "are all agents live, on what data, and doing what?".
"""

from __future__ import annotations

from dataclasses import dataclass

from atlas_ai.application.orchestration.roster import AGENT_PROFILES
from atlas_ai.application.prediction.engine import AGENT_WEIGHTS
from atlas_ai.domain.enums import AgentKind


@dataclass(frozen=True, slots=True)
class AgentStatus:
    """A live view of one agent: what it does, on what data, at what weight."""

    kind: AgentKind
    role: str
    responsibilities: tuple[str, ...]
    data_basis: str
    weight: float | None  # blend weight for scored agents; None for synthesis stages
    status: str


@dataclass(frozen=True, slots=True)
class SystemStatus:
    """The orchestrator's whole-system status report."""

    app_name: str
    version: str
    adapter_mode: str
    pipeline_version: str
    agent_count: int
    live_on_real_data: int
    agents: tuple[AgentStatus, ...]
    ceo_mandate: str
    coo_operations: str
    cto_readiness: str
    readiness_notes: tuple[str, ...]


_CEO_MANDATE = (
    "Deliver institutional-grade AI investment *research* for Indian markets: "
    "every output carries confidence, assumptions, risks, evidence, and a "
    "not-advice disclaimer. No deterministic predictions, ever."
)


class Orchestrator:
    """Coordinates the agent fleet and reports a single honest status."""

    def __init__(
        self,
        *,
        app_name: str,
        version: str,
        adapter_mode: str,
        pipeline_version: str,
        data_basis: dict[AgentKind, str],
        readiness_notes: tuple[str, ...],
    ) -> None:
        self._app_name = app_name
        self._version = version
        self._adapter_mode = adapter_mode
        self._pipeline_version = pipeline_version
        self._data_basis = data_basis
        self._readiness_notes = readiness_notes

    def status(self) -> SystemStatus:
        agents = tuple(
            AgentStatus(
                kind=kind,
                role=profile.role,
                responsibilities=profile.responsibilities,
                data_basis=self._data_basis.get(kind, "derived from other agents"),
                weight=AGENT_WEIGHTS.get(kind),
                status="operational",
            )
            for kind, profile in AGENT_PROFILES.items()
        )
        # The "(real)" marker denotes a genuine live feed; "(real adapter
        # pending)" and "derived"/synthesis bases deliberately do not match.
        live_real = sum(1 for a in agents if "(real)" in a.data_basis)
        scored = sum(1 for a in agents if a.weight is not None)
        synthesis = len(agents) - scored
        coo = (
            f"{len(agents)} agents operational ({scored} scored specialists blended "
            f"into the edge, {synthesis} synthesis stages) via {self._pipeline_version}."
        )
        cto = (
            "All agents live on real data."
            if not self._readiness_notes
            else f"Live, with {len(self._readiness_notes)} surface(s) on non-real data."
        )
        return SystemStatus(
            app_name=self._app_name,
            version=self._version,
            adapter_mode=self._adapter_mode,
            pipeline_version=self._pipeline_version,
            agent_count=len(agents),
            live_on_real_data=live_real,
            agents=agents,
            ceo_mandate=_CEO_MANDATE,
            coo_operations=coo,
            cto_readiness=cto,
            readiness_notes=self._readiness_notes,
        )
