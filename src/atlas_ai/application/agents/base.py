"""Agent contract and the shared context threaded through the pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from atlas_ai.domain.analysis import AgentReport
from atlas_ai.domain.enums import AgentKind
from atlas_ai.domain.market import Candle, Fundamentals, Instrument, Quote


@dataclass
class AgentContext:
    """Everything an agent needs to reason, plus space for prior reports.

    The context is populated by the data-gathering step and then threaded through
    the agents; each analysis agent reads what it needs and contributes a report.
    """

    instrument: Instrument
    quote: Quote
    candles: list[Candle]
    fundamentals: Fundamentals
    capital: float
    reports: dict[AgentKind, AgentReport] = field(default_factory=dict)

    def report(self, kind: AgentKind) -> AgentReport | None:
        return self.reports.get(kind)


@runtime_checkable
class AnalysisAgent(Protocol):
    """An agent that reduces the context to a single explainable report."""

    kind: AgentKind

    def analyze(self, ctx: AgentContext) -> AgentReport: ...
