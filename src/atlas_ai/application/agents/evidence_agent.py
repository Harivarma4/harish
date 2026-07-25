"""Evidence agent — turns signals and debate into attributable evidence.

Assembles supporting and counter evidence, catalysts, and explicit unknowns so
every recommendation can answer: why, why now, why not, and on what basis.
"""

from __future__ import annotations

from dataclasses import dataclass

from atlas_ai.application.agents.base import AgentContext
from atlas_ai.domain.analysis import AgentReport
from atlas_ai.domain.debate import DebateOutcome
from atlas_ai.domain.enums import AgentKind, SignalStrength
from atlas_ai.domain.evidence import Evidence, Source

_SOURCES = {
    AgentKind.FUNDAMENTAL: Source("Atlas fundamental engine", 0.85),
    AgentKind.TECHNICAL: Source("Atlas technical engine", 0.7),
    AgentKind.MACRO: Source("Atlas macro engine", 0.75),
    AgentKind.NEWS: Source("Atlas news-sentiment engine", 0.6),
    AgentKind.RISK: Source("Atlas risk model", 0.8),
}


@dataclass(frozen=True, slots=True)
class EvidenceBundle:
    """Everything the synthesizer needs to justify and caveat a recommendation."""

    evidence: tuple[Evidence, ...]
    catalysts: tuple[str, ...]
    counter_arguments: tuple[str, ...]
    unknown_risks: tuple[str, ...]


class EvidenceAgent:
    """Builds the evidence bundle from reports and the debate outcome."""

    def assemble(
        self, ctx: AgentContext, reports: list[AgentReport], debate: DebateOutcome
    ) -> EvidenceBundle:
        evidence: list[Evidence] = []
        for r in reports:
            source = _SOURCES.get(r.agent, Source(f"Atlas {r.agent.value.lower()} engine", 0.6))
            for s in r.signals:
                if s.strength is SignalStrength.NEUTRAL:
                    continue
                weight = s.directional_score  # negative -> counter-evidence
                evidence.append(
                    Evidence(
                        claim=f"{s.name}: {s.detail} = {s.value}",
                        source=source,
                        weight=round(weight, 3),
                    )
                )
        if not evidence:
            evidence.append(
                Evidence(
                    claim="Signals are balanced; no directional edge detected.",
                    source=Source("Atlas synthesis", 0.6),
                    weight=0.0,
                )
            )

        catalysts = self._catalysts(ctx)
        counter_arguments = tuple(
            e.claim for e in evidence if e.is_counter
        ) or (debate.bear.thesis,)
        unknown_risks = (
            "Macro regime shifts (rates, currency, oil) not modelled in this pass.",
            "Event risk (regulatory action, management change) is not yet ingested.",
            "Liquidity and slippage at execution are estimated, not observed.",
        )
        return EvidenceBundle(
            evidence=tuple(evidence),
            catalysts=catalysts,
            counter_arguments=counter_arguments,
            unknown_risks=unknown_risks,
        )

    def _catalysts(self, ctx: AgentContext) -> tuple[str, ...]:
        f = ctx.fundamentals
        catalysts: list[str] = []
        if f.earnings_growth_pct >= 15:
            catalysts.append(f"Earnings compounding at {f.earnings_growth_pct:.0f}% YoY.")
        if f.revenue_growth_pct >= 12:
            catalysts.append(f"Revenue growth of {f.revenue_growth_pct:.0f}% YoY.")
        if f.debt_to_equity < 0.5:
            catalysts.append("Clean balance sheet enables re-rating.")
        if not catalysts:
            catalysts.append("No standout near-term catalyst; thesis is valuation-driven.")
        return tuple(catalysts)
