"""ResearchPipeline — wires the agents into the end-to-end research flow.

    data → [fundamental, technical, macro, news] → risk → debate → prediction → evidence

The pipeline produces a structured result; turning that result into a persisted
``Recommendation`` is the job of the use case, keeping orchestration and
application policy separate.
"""

from __future__ import annotations

from dataclasses import dataclass

from atlas_ai.application.agents.base import AgentContext
from atlas_ai.application.agents.debate_agent import DebateAgent
from atlas_ai.application.agents.evidence_agent import EvidenceAgent, EvidenceBundle
from atlas_ai.application.agents.fundamental_agent import FundamentalAgent
from atlas_ai.application.agents.macro_agent import MacroAgent
from atlas_ai.application.agents.news_agent import NewsAgent
from atlas_ai.application.agents.risk_agent import RiskAgent
from atlas_ai.application.agents.technical_agent import TechnicalAgent
from atlas_ai.application.orchestration.graph import AgentGraph
from atlas_ai.application.prediction.engine import PredictionEngine
from atlas_ai.domain.analysis import AgentReport
from atlas_ai.domain.debate import DebateOutcome
from atlas_ai.domain.forecast import ProbabilisticOutlook
from atlas_ai.domain.risk import RiskAssessment

PIPELINE_VERSION = "research-pipeline-v1"


@dataclass(frozen=True, slots=True)
class PipelineResult:
    """The full analytical output before synthesis into a recommendation."""

    reports: tuple[AgentReport, ...]
    risk: RiskAssessment
    debate: DebateOutcome
    outlook: ProbabilisticOutlook
    evidence: EvidenceBundle


class ResearchPipeline:
    def __init__(
        self,
        *,
        fundamental: FundamentalAgent,
        technical: TechnicalAgent,
        macro: MacroAgent,
        news: NewsAgent,
        risk: RiskAgent,
        debate: DebateAgent,
        evidence: EvidenceAgent,
        prediction: PredictionEngine,
    ) -> None:
        self._graph = AgentGraph([fundamental, technical, macro, news])
        self._risk = risk
        self._debate = debate
        self._evidence = evidence
        self._prediction = prediction

    def run(self, ctx: AgentContext, *, horizon_days: int) -> PipelineResult:
        # 1. Analysis agents (fundamental + technical + macro + news) populate the context.
        reports = self._graph.run(ctx)

        # 2. Risk plan, and fold its report into the analytical set.
        risk_assessment, risk_report = self._risk.assess(ctx)
        ctx.reports[risk_report.agent] = risk_report
        reports = [*reports, risk_report]

        # 3. Bull/bear/judge debate over all reports.
        debate = self._debate.debate(ctx, reports)

        # 4. Probabilistic outlook (Bayesian blend + Monte Carlo).
        outlook = self._prediction.forecast(ctx, reports, debate, horizon_days=horizon_days)

        # 5. Evidence, catalysts, counter-arguments, unknowns.
        evidence = self._evidence.assemble(ctx, reports, debate)

        return PipelineResult(
            reports=tuple(reports),
            risk=risk_assessment,
            debate=debate,
            outlook=outlook,
            evidence=evidence,
        )
