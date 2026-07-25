"""Lossless serialization between the ``Recommendation`` aggregate and JSON.

The persistence layer stores recommendations as JSONB. Because the aggregate is a
graph of frozen, self-validating value objects, we serialize it explicitly (no
generic reflection) so the wire shape is stable and auditable, and reconstruct it
field-by-field on read. Frozen dataclass equality makes this round-trip testable:
``from_dict(to_dict(rec)) == rec``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from atlas_ai.application.ports.repositories import AuditRecord
from atlas_ai.domain.analysis import AgentReport, Signal
from atlas_ai.domain.debate import DebateArgument, DebateOutcome
from atlas_ai.domain.enums import (
    Action,
    AgentKind,
    Conviction,
    Exchange,
    SignalStrength,
    TimeHorizon,
)
from atlas_ai.domain.evidence import Evidence, Source
from atlas_ai.domain.forecast import ProbabilisticOutlook
from atlas_ai.domain.governance import GovernanceMetadata
from atlas_ai.domain.market import Instrument
from atlas_ai.domain.recommendation import Recommendation
from atlas_ai.domain.risk import RiskAssessment
from atlas_ai.domain.value_objects import Confidence, Money, Percent, Score

# -- Recommendation ----------------------------------------------------------

def recommendation_to_dict(rec: Recommendation) -> dict[str, Any]:
    return {
        "id": rec.id,
        "instrument": _instrument_to_dict(rec.instrument),
        "action": rec.action.value,
        "conviction": rec.conviction.value,
        "confidence": rec.confidence.value,
        "time_horizon": rec.time_horizon.value,
        "executive_summary": rec.executive_summary,
        "outlook": _outlook_to_dict(rec.outlook),
        "risk": _risk_to_dict(rec.risk),
        "debate": _debate_to_dict(rec.debate),
        "agent_reports": [_report_to_dict(r) for r in rec.agent_reports],
        "catalysts": list(rec.catalysts),
        "assumptions": list(rec.assumptions),
        "known_risks": list(rec.known_risks),
        "unknown_risks": list(rec.unknown_risks),
        "counter_arguments": list(rec.counter_arguments),
        "evidence": [_evidence_to_dict(e) for e in rec.evidence],
        "governance": _governance_to_dict(rec.governance),
        "disclaimer": rec.disclaimer,
    }


def recommendation_from_dict(data: dict[str, Any]) -> Recommendation:
    return Recommendation(
        instrument=_instrument_from_dict(data["instrument"]),
        action=Action(data["action"]),
        conviction=Conviction(data["conviction"]),
        confidence=Confidence(data["confidence"]),
        time_horizon=TimeHorizon(data["time_horizon"]),
        executive_summary=data["executive_summary"],
        outlook=_outlook_from_dict(data["outlook"]),
        risk=_risk_from_dict(data["risk"]),
        debate=_debate_from_dict(data["debate"]),
        agent_reports=tuple(_report_from_dict(r) for r in data["agent_reports"]),
        catalysts=tuple(data["catalysts"]),
        assumptions=tuple(data["assumptions"]),
        known_risks=tuple(data["known_risks"]),
        unknown_risks=tuple(data["unknown_risks"]),
        counter_arguments=tuple(data["counter_arguments"]),
        evidence=tuple(_evidence_from_dict(e) for e in data["evidence"]),
        governance=_governance_from_dict(data["governance"]),
        id=data["id"],
        disclaimer=data["disclaimer"],
    )


# -- AuditRecord -------------------------------------------------------------

def audit_to_dict(record: AuditRecord) -> dict[str, Any]:
    return {
        "recommendation_id": record.recommendation_id,
        "action": record.action,
        "instrument_key": record.instrument_key,
        "confidence": record.confidence,
        "model_version": record.model_version,
        "prompt_version": record.prompt_version,
        "pipeline_version": record.pipeline_version,
        "reasoning_summary": record.reasoning_summary,
        "created_at": record.created_at.isoformat(),
    }


def audit_from_dict(data: dict[str, Any]) -> AuditRecord:
    return AuditRecord(
        recommendation_id=data["recommendation_id"],
        action=data["action"],
        instrument_key=data["instrument_key"],
        confidence=data["confidence"],
        model_version=data["model_version"],
        prompt_version=data["prompt_version"],
        pipeline_version=data["pipeline_version"],
        reasoning_summary=data["reasoning_summary"],
        created_at=_parse_dt(data["created_at"]),
    )


# -- internals ---------------------------------------------------------------

def _instrument_to_dict(i: Instrument) -> dict[str, Any]:
    return {"symbol": i.symbol, "exchange": i.exchange.value, "name": i.name}


def _instrument_from_dict(d: dict[str, Any]) -> Instrument:
    return Instrument(symbol=d["symbol"], exchange=Exchange(d["exchange"]), name=d["name"])


def _outlook_to_dict(o: ProbabilisticOutlook) -> dict[str, Any]:
    return {
        "probability_favourable": o.probability_favourable,
        "expected_cagr": o.expected_cagr.value,
        "cagr_p05": o.cagr_p05.value,
        "cagr_p95": o.cagr_p95.value,
        "confidence": o.confidence.value,
        "simulations": o.simulations,
    }


def _outlook_from_dict(d: dict[str, Any]) -> ProbabilisticOutlook:
    return ProbabilisticOutlook(
        probability_favourable=d["probability_favourable"],
        expected_cagr=Percent(d["expected_cagr"]),
        cagr_p05=Percent(d["cagr_p05"]),
        cagr_p95=Percent(d["cagr_p95"]),
        confidence=Confidence(d["confidence"]),
        simulations=d["simulations"],
    )


def _risk_to_dict(r: RiskAssessment) -> dict[str, Any]:
    return {
        "entry_price": r.entry_price,
        "stop_loss": r.stop_loss,
        "target_price": r.target_price,
        "quantity": r.quantity,
        "capital_at_risk": _money_to_dict(r.capital_at_risk),
        "position_value": _money_to_dict(r.position_value),
        "reward_to_risk": r.reward_to_risk,
        "value_at_risk_pct": r.value_at_risk_pct.value,
        "var_confidence": r.var_confidence,
    }


def _risk_from_dict(d: dict[str, Any]) -> RiskAssessment:
    return RiskAssessment(
        entry_price=d["entry_price"],
        stop_loss=d["stop_loss"],
        target_price=d["target_price"],
        quantity=d["quantity"],
        capital_at_risk=_money_from_dict(d["capital_at_risk"]),
        position_value=_money_from_dict(d["position_value"]),
        reward_to_risk=d["reward_to_risk"],
        value_at_risk_pct=Percent(d["value_at_risk_pct"]),
        var_confidence=d["var_confidence"],
    )


def _money_to_dict(m: Money) -> dict[str, Any]:
    return {"amount": m.amount, "currency": m.currency}


def _money_from_dict(d: dict[str, Any]) -> Money:
    return Money(amount=d["amount"], currency=d["currency"])


def _debate_to_dict(o: DebateOutcome) -> dict[str, Any]:
    return {
        "bull": _argument_to_dict(o.bull),
        "bear": _argument_to_dict(o.bear),
        "verdict": o.verdict,
        "leaning": o.leaning,
    }


def _debate_from_dict(d: dict[str, Any]) -> DebateOutcome:
    return DebateOutcome(
        bull=_argument_from_dict(d["bull"]),
        bear=_argument_from_dict(d["bear"]),
        verdict=d["verdict"],
        leaning=d["leaning"],
    )


def _argument_to_dict(a: DebateArgument) -> dict[str, Any]:
    return {"stance": a.stance, "thesis": a.thesis, "points": list(a.points)}


def _argument_from_dict(d: dict[str, Any]) -> DebateArgument:
    return DebateArgument(stance=d["stance"], thesis=d["thesis"], points=tuple(d["points"]))


def _report_to_dict(r: AgentReport) -> dict[str, Any]:
    return {
        "agent": r.agent.value,
        "score": r.score.value,
        "signals": [_signal_to_dict(s) for s in r.signals],
        "rationale": r.rationale,
        "assumptions": list(r.assumptions),
        "risks": list(r.risks),
    }


def _report_from_dict(d: dict[str, Any]) -> AgentReport:
    return AgentReport(
        agent=AgentKind(d["agent"]),
        score=Score(d["score"]),
        signals=tuple(_signal_from_dict(s) for s in d["signals"]),
        rationale=d["rationale"],
        assumptions=tuple(d["assumptions"]),
        risks=tuple(d["risks"]),
    )


def _signal_to_dict(s: Signal) -> dict[str, Any]:
    return {
        "name": s.name,
        "strength": s.strength.value,
        "detail": s.detail,
        "value": s.value,
    }


def _signal_from_dict(d: dict[str, Any]) -> Signal:
    return Signal(
        name=d["name"],
        strength=SignalStrength(d["strength"]),
        detail=d["detail"],
        value=d["value"],
    )


def _evidence_to_dict(e: Evidence) -> dict[str, Any]:
    return {
        "claim": e.claim,
        "source": _source_to_dict(e.source),
        "weight": e.weight,
        "observed_at": e.observed_at.isoformat(),
    }


def _evidence_from_dict(d: dict[str, Any]) -> Evidence:
    return Evidence(
        claim=d["claim"],
        source=_source_from_dict(d["source"]),
        weight=d["weight"],
        observed_at=_parse_dt(d["observed_at"]),
    )


def _source_to_dict(s: Source) -> dict[str, Any]:
    return {"name": s.name, "reliability": s.reliability, "url": s.url}


def _source_from_dict(d: dict[str, Any]) -> Source:
    return Source(name=d["name"], reliability=d["reliability"], url=d["url"])


def _governance_to_dict(g: GovernanceMetadata) -> dict[str, Any]:
    return {
        "model_version": g.model_version,
        "prompt_version": g.prompt_version,
        "pipeline_version": g.pipeline_version,
        "reasoning_summary": g.reasoning_summary,
        "generated_at": g.generated_at.isoformat(),
    }


def _governance_from_dict(d: dict[str, Any]) -> GovernanceMetadata:
    return GovernanceMetadata(
        model_version=d["model_version"],
        prompt_version=d["prompt_version"],
        pipeline_version=d["pipeline_version"],
        reasoning_summary=d["reasoning_summary"],
        generated_at=_parse_dt(d["generated_at"]),
    )


def _parse_dt(raw: str) -> datetime:
    return datetime.fromisoformat(raw)
