"""The Recommendation aggregate — the platform's central output.

Invariant: a recommendation is only valid as *research* if it is accompanied by
its uncertainty and its justification. The constructor therefore refuses to build
a recommendation that lacks confidence, assumptions, risks, evidence, or the
disclaimer. This makes "certainty theatre" structurally impossible.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from atlas_ai.domain.analysis import AgentReport
from atlas_ai.domain.debate import DebateOutcome
from atlas_ai.domain.enums import Action, Conviction, TimeHorizon
from atlas_ai.domain.evidence import Evidence
from atlas_ai.domain.forecast import ProbabilisticOutlook
from atlas_ai.domain.governance import GovernanceMetadata
from atlas_ai.domain.market import Instrument
from atlas_ai.domain.risk import RiskAssessment
from atlas_ai.domain.value_objects import Confidence

DISCLAIMER = (
    "This is AI-generated investment research, not investment advice. It carries "
    "no guarantee of returns and makes no deterministic prediction. Consult a "
    "SEBI-registered investment adviser before acting."
)


@dataclass(frozen=True, slots=True)
class Recommendation:
    """A complete, explainable, evidence-backed research recommendation."""

    instrument: Instrument
    action: Action
    conviction: Conviction
    confidence: Confidence
    time_horizon: TimeHorizon
    executive_summary: str

    outlook: ProbabilisticOutlook
    risk: RiskAssessment
    debate: DebateOutcome

    agent_reports: tuple[AgentReport, ...]
    catalysts: tuple[str, ...]
    assumptions: tuple[str, ...]
    known_risks: tuple[str, ...]
    unknown_risks: tuple[str, ...]
    counter_arguments: tuple[str, ...]
    evidence: tuple[Evidence, ...]

    governance: GovernanceMetadata
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    disclaimer: str = DISCLAIMER

    def __post_init__(self) -> None:
        # Guardrail invariants: research must be uncertain, justified, and framed.
        if not self.assumptions:
            raise ValueError("A recommendation must state its assumptions.")
        if not self.known_risks:
            raise ValueError("A recommendation must state its known risks.")
        if not self.evidence:
            raise ValueError("A recommendation must cite supporting evidence.")
        if not self.executive_summary.strip():
            raise ValueError("A recommendation must include an executive summary.")
        if not self.disclaimer.strip():
            raise ValueError("A recommendation must carry a disclaimer.")

    @property
    def supporting_evidence(self) -> tuple[Evidence, ...]:
        return tuple(e for e in self.evidence if not e.is_counter)

    @property
    def counter_evidence(self) -> tuple[Evidence, ...]:
        return tuple(e for e in self.evidence if e.is_counter)
