"""Use case: generate, synthesize, persist, and audit a recommendation."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime

from atlas_ai.application.agents.base import AgentContext
from atlas_ai.application.orchestration.pipeline import (
    PIPELINE_VERSION,
    PipelineResult,
    ResearchPipeline,
)
from atlas_ai.application.ports.market_data import MarketDataPort
from atlas_ai.application.ports.repositories import (
    AuditRecord,
    AuditRepository,
    RecommendationRepository,
)
from atlas_ai.domain.enums import Action, Conviction, Exchange, TimeHorizon
from atlas_ai.domain.governance import GovernanceMetadata
from atlas_ai.domain.market import Instrument
from atlas_ai.domain.recommendation import Recommendation

_HORIZON_DAYS = {
    TimeHorizon.INTRADAY: 1,
    TimeHorizon.SHORT_TERM: 21,
    TimeHorizon.MEDIUM_TERM: 126,
    TimeHorizon.LONG_TERM: 252,
}


@dataclass(frozen=True, slots=True)
class GenerateRecommendationCommand:
    symbol: str
    exchange: Exchange = Exchange.NSE
    capital: float = 100_000.0
    time_horizon: TimeHorizon = TimeHorizon.MEDIUM_TERM
    candle_days: int = 260


class GenerateRecommendation:
    """Coordinates data gathering, the research pipeline, and persistence."""

    def __init__(
        self,
        *,
        market_data: MarketDataPort,
        pipeline: ResearchPipeline,
        repository: RecommendationRepository,
        audit: AuditRepository,
        model_version: str,
        prompt_version: str = "debate-v1",
    ) -> None:
        self._market_data = market_data
        self._pipeline = pipeline
        self._repository = repository
        self._audit = audit
        self._model_version = model_version
        self._prompt_version = prompt_version

    def execute(self, command: GenerateRecommendationCommand) -> Recommendation:
        instrument = Instrument(symbol=command.symbol.upper(), exchange=command.exchange)

        # 1. Gather data through the port (mock or real).
        quote = self._market_data.get_quote(instrument)
        candles = self._market_data.get_candles(instrument, days=command.candle_days)
        fundamentals = self._market_data.get_fundamentals(instrument)
        ctx = AgentContext(
            instrument=instrument,
            quote=quote,
            candles=candles,
            fundamentals=fundamentals,
            capital=command.capital,
        )

        # 2. Run the multi-agent research pipeline.
        horizon_days = _HORIZON_DAYS[command.time_horizon]
        result = self._pipeline.run(ctx, horizon_days=horizon_days)

        # 3. Synthesize the recommendation.
        recommendation = self._synthesize(instrument, command, result)

        # 4. Persist + write an immutable audit record.
        self._repository.save(recommendation)
        self._audit.append(self._audit_record(recommendation))
        return recommendation

    def _synthesize(
        self,
        instrument: Instrument,
        command: GenerateRecommendationCommand,
        result: PipelineResult,
    ) -> Recommendation:
        outlook = result.outlook
        action = self._classify_action(outlook.probability_favourable, outlook.expected_cagr.value)
        conviction = Conviction.from_confidence(outlook.confidence.value)

        assumptions = _dedupe(a for r in result.reports for a in r.assumptions)
        known_risks = _dedupe(risk for r in result.reports for risk in r.risks)

        summary = (
            f"{action.value} {instrument.symbol} ({conviction.value} conviction, "
            f"{outlook.confidence.as_percent():.0f}% confidence). "
            f"Modelled {outlook.probability_favourable:.0%} probability of a favourable "
            f"{command.time_horizon.value.lower().replace('_', ' ')} outcome; "
            f"expected CAGR {outlook.expected_cagr.value:.1f}% "
            f"(90% CI {outlook.cagr_p05.value:.1f}%..{outlook.cagr_p95.value:.1f}%). "
            f"Reward:risk {result.risk.reward_to_risk}. {result.debate.verdict}"
        )
        reasoning_summary = (
            f"Blended {len(result.reports)} agent reports "
            f"({', '.join(r.agent.value for r in result.reports)}); debate leaning "
            f"{result.debate.leaning:+.2f}; {outlook.simulations} Monte Carlo paths over "
            f"{command.time_horizon.value}."
        )

        return Recommendation(
            instrument=instrument,
            action=action,
            conviction=conviction,
            confidence=outlook.confidence,
            time_horizon=command.time_horizon,
            executive_summary=summary,
            outlook=outlook,
            risk=result.risk,
            debate=result.debate,
            agent_reports=result.reports,
            catalysts=result.evidence.catalysts,
            assumptions=assumptions,
            known_risks=known_risks,
            unknown_risks=result.evidence.unknown_risks,
            counter_arguments=result.evidence.counter_arguments,
            evidence=result.evidence.evidence,
            governance=GovernanceMetadata(
                model_version=self._model_version,
                prompt_version=self._prompt_version,
                pipeline_version=PIPELINE_VERSION,
                reasoning_summary=reasoning_summary,
            ),
        )

    @staticmethod
    def _classify_action(probability: float, expected_cagr: float) -> Action:
        if probability >= 0.62 and expected_cagr > 0:
            return Action.BUY
        if probability >= 0.55:
            return Action.ACCUMULATE
        if probability >= 0.45:
            return Action.HOLD
        if probability >= 0.38:
            return Action.REDUCE
        return Action.SELL if expected_cagr < 0 else Action.AVOID

    def _audit_record(self, rec: Recommendation) -> AuditRecord:
        return AuditRecord(
            recommendation_id=rec.id,
            action=rec.action.value,
            instrument_key=rec.instrument.key,
            confidence=rec.confidence.value,
            model_version=rec.governance.model_version,
            prompt_version=rec.governance.prompt_version,
            pipeline_version=rec.governance.pipeline_version,
            reasoning_summary=rec.governance.reasoning_summary,
            created_at=datetime.now(UTC),
        )


def _dedupe(items: Iterable[str]) -> tuple[str, ...]:
    """Order-preserving de-duplication of an iterable of strings."""
    seen: dict[str, None] = {}
    for item in items:
        seen.setdefault(item, None)
    return tuple(seen)
