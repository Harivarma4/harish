"""A minimal typed DAG runner for analysis agents.

Nodes are analysis agents; the runner executes them in registration order and
collects their reports into the shared context. Ordering is deterministic, which
keeps runs reproducible. This is intentionally tiny — dependency edges and
parallelism can be added here without changing agent code.
"""

from __future__ import annotations

from atlas_ai.application.agents.base import AgentContext, AnalysisAgent
from atlas_ai.domain.analysis import AgentReport


class AgentGraph:
    """Runs a fixed sequence of analysis agents over a context."""

    def __init__(self, agents: list[AnalysisAgent]) -> None:
        if not agents:
            raise ValueError("AgentGraph requires at least one agent")
        self._agents = agents

    def run(self, ctx: AgentContext) -> list[AgentReport]:
        reports: list[AgentReport] = []
        for agent in self._agents:
            report = agent.analyze(ctx)
            ctx.reports[agent.kind] = report
            reports.append(report)
        return reports
