"""API DTOs and mapping from domain objects to response models.

DTOs are deliberately separate from domain entities so the wire format can evolve
independently of the model.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from atlas_ai.domain.enums import Exchange, TimeHorizon
from atlas_ai.domain.recommendation import Recommendation


class RecommendationRequest(BaseModel):
    symbol: str = Field(..., examples=["RELIANCE"], min_length=1)
    exchange: Exchange = Exchange.NSE
    capital: float = Field(default=100_000.0, gt=0)
    time_horizon: TimeHorizon = TimeHorizon.MEDIUM_TERM


class SignalDTO(BaseModel):
    name: str
    strength: str
    detail: str
    value: float | None


class AgentReportDTO(BaseModel):
    agent: str
    score: float
    rationale: str
    signals: list[SignalDTO]
    assumptions: list[str]
    risks: list[str]


class EvidenceDTO(BaseModel):
    claim: str
    source: str
    source_reliability: float
    weight: float
    is_counter: bool


class OutlookDTO(BaseModel):
    probability_favourable: float
    expected_cagr_pct: float
    cagr_p05_pct: float
    cagr_p95_pct: float
    confidence: float
    simulations: int


class RiskDTO(BaseModel):
    entry_price: float
    stop_loss: float
    target_price: float
    quantity: int
    position_value: float
    capital_at_risk: float
    reward_to_risk: float
    value_at_risk_pct: float
    var_confidence: float


class DebateDTO(BaseModel):
    bull_thesis: str
    bear_thesis: str
    verdict: str
    leaning: float


class GovernanceDTO(BaseModel):
    model_version: str
    prompt_version: str
    pipeline_version: str
    reasoning_summary: str
    generated_at: datetime


class RecommendationResponse(BaseModel):
    id: str
    symbol: str
    exchange: str
    action: str
    conviction: str
    confidence: float
    time_horizon: str
    executive_summary: str

    outlook: OutlookDTO
    risk: RiskDTO
    debate: DebateDTO

    agent_reports: list[AgentReportDTO]
    catalysts: list[str]
    assumptions: list[str]
    known_risks: list[str]
    unknown_risks: list[str]
    counter_arguments: list[str]
    evidence: list[EvidenceDTO]

    governance: GovernanceDTO
    disclaimer: str


def to_response(rec: Recommendation) -> RecommendationResponse:
    return RecommendationResponse(
        id=rec.id,
        symbol=rec.instrument.symbol,
        exchange=rec.instrument.exchange.value,
        action=rec.action.value,
        conviction=rec.conviction.value,
        confidence=rec.confidence.value,
        time_horizon=rec.time_horizon.value,
        executive_summary=rec.executive_summary,
        outlook=OutlookDTO(
            probability_favourable=rec.outlook.probability_favourable,
            expected_cagr_pct=rec.outlook.expected_cagr.value,
            cagr_p05_pct=rec.outlook.cagr_p05.value,
            cagr_p95_pct=rec.outlook.cagr_p95.value,
            confidence=rec.outlook.confidence.value,
            simulations=rec.outlook.simulations,
        ),
        risk=RiskDTO(
            entry_price=rec.risk.entry_price,
            stop_loss=rec.risk.stop_loss,
            target_price=rec.risk.target_price,
            quantity=rec.risk.quantity,
            position_value=rec.risk.position_value.amount,
            capital_at_risk=rec.risk.capital_at_risk.amount,
            reward_to_risk=rec.risk.reward_to_risk,
            value_at_risk_pct=rec.risk.value_at_risk_pct.value,
            var_confidence=rec.risk.var_confidence,
        ),
        debate=DebateDTO(
            bull_thesis=rec.debate.bull.thesis,
            bear_thesis=rec.debate.bear.thesis,
            verdict=rec.debate.verdict,
            leaning=rec.debate.leaning,
        ),
        agent_reports=[
            AgentReportDTO(
                agent=r.agent.value,
                score=r.score.value,
                rationale=r.rationale,
                signals=[
                    SignalDTO(
                        name=s.name, strength=s.strength.value, detail=s.detail, value=s.value
                    )
                    for s in r.signals
                ],
                assumptions=list(r.assumptions),
                risks=list(r.risks),
            )
            for r in rec.agent_reports
        ],
        catalysts=list(rec.catalysts),
        assumptions=list(rec.assumptions),
        known_risks=list(rec.known_risks),
        unknown_risks=list(rec.unknown_risks),
        counter_arguments=list(rec.counter_arguments),
        evidence=[
            EvidenceDTO(
                claim=e.claim,
                source=e.source.name,
                source_reliability=e.source.reliability,
                weight=e.weight,
                is_counter=e.is_counter,
            )
            for e in rec.evidence
        ],
        governance=GovernanceDTO(
            model_version=rec.governance.model_version,
            prompt_version=rec.governance.prompt_version,
            pipeline_version=rec.governance.pipeline_version,
            reasoning_summary=rec.governance.reasoning_summary,
            generated_at=rec.governance.generated_at,
        ),
        disclaimer=rec.disclaimer,
    )
