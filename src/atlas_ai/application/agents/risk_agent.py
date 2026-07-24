"""Risk agent — position sizing, ATR-based stops, reward:risk, and VaR."""

from __future__ import annotations

from dataclasses import dataclass
from math import floor

import numpy as np

from atlas_ai.application.agents.base import AgentContext
from atlas_ai.application.agents.indicators import atr
from atlas_ai.domain.analysis import AgentReport, Signal
from atlas_ai.domain.enums import AgentKind, SignalStrength
from atlas_ai.domain.risk import RiskAssessment
from atlas_ai.domain.value_objects import Money, Percent


@dataclass(frozen=True, slots=True)
class RiskPolicy:
    """Configurable risk controls."""

    risk_fraction_per_trade: float = 0.01   # fraction of capital risked per trade
    atr_stop_multiple: float = 2.0
    reward_to_risk: float = 2.0
    var_confidence: float = 0.95


class RiskAgent:
    """Derives a concrete, sized risk plan and a companion report."""

    kind = AgentKind.RISK

    def __init__(self, policy: RiskPolicy | None = None) -> None:
        self.policy = policy or RiskPolicy()

    def assess(self, ctx: AgentContext) -> tuple[RiskAssessment, AgentReport]:
        p = self.policy
        entry = ctx.quote.last_price
        a = atr(ctx.candles) or max(entry * 0.02, 0.01)  # fallback: 2% of price

        stop = max(entry - p.atr_stop_multiple * a, 0.01)
        risk_per_share = max(entry - stop, 0.01)
        target = entry + p.reward_to_risk * risk_per_share

        budget = ctx.capital * p.risk_fraction_per_trade
        quantity = max(floor(budget / risk_per_share), 0)
        # Never size a position larger than available capital.
        if quantity * entry > ctx.capital:
            quantity = floor(ctx.capital / entry)

        capital_at_risk = Money(round(quantity * risk_per_share, 2))
        position_value = Money(round(quantity * entry, 2))
        reward_to_risk = round((target - entry) / risk_per_share, 2)
        var_pct = self._historical_var(ctx, p.var_confidence)

        assessment = RiskAssessment(
            entry_price=round(entry, 2),
            stop_loss=round(stop, 2),
            target_price=round(target, 2),
            quantity=quantity,
            capital_at_risk=capital_at_risk,
            position_value=position_value,
            reward_to_risk=reward_to_risk,
            value_at_risk_pct=Percent(round(var_pct, 2)),
            var_confidence=p.var_confidence,
        )
        report = self._report(assessment)
        return assessment, report

    def _historical_var(self, ctx: AgentContext, confidence: float) -> float:
        closes = np.array([c.close for c in ctx.candles], dtype=float)
        if closes.size < 2:
            return 0.0
        returns = np.diff(closes) / closes[:-1]
        loss_quantile = float(np.percentile(returns, (1.0 - confidence) * 100.0))
        return abs(min(loss_quantile, 0.0)) * 100.0

    def _report(self, a: RiskAssessment) -> AgentReport:
        # A healthy reward:risk (>=2) is constructive; a thin one is not.
        if a.reward_to_risk >= 2.0:
            strength = SignalStrength.BULLISH
        elif a.reward_to_risk >= 1.0:
            strength = SignalStrength.NEUTRAL
        else:
            strength = SignalStrength.BEARISH
        signals = (
            Signal("RewardRisk", strength, "Target vs stop distance", a.reward_to_risk),
            Signal(
                "VaR",
                SignalStrength.BEARISH if a.value_at_risk_pct.value > 4 else SignalStrength.NEUTRAL,
                f"1-day {a.var_confidence:.0%} historical VaR",
                a.value_at_risk_pct.value,
            ),
        )
        rationale = (
            f"Entry {a.entry_price}, stop {a.stop_loss}, target {a.target_price}; "
            f"size {a.quantity} (position {a.position_value}, capital at risk "
            f"{a.capital_at_risk}); R:R {a.reward_to_risk}; "
            f"1-day VaR {a.value_at_risk_pct.value:.2f}% @ {a.var_confidence:.0%}."
        )
        # Risk scoring: reward the plan's favourability, penalize fat tails.
        from atlas_ai.domain.value_objects import Score

        raw = 50.0 + (a.reward_to_risk - 1.0) * 15.0 - a.value_at_risk_pct.value * 3.0
        score = Score(min(max(round(raw, 2), 0.0), 100.0))
        return AgentReport(
            agent=self.kind,
            score=score,
            signals=signals,
            rationale=rationale,
            assumptions=(
                f"Fixed fractional sizing risks {self.policy.risk_fraction_per_trade:.0%} "
                "of capital per trade.",
                "Historical volatility is representative of the holding period.",
            ),
            risks=(
                "Stops can gap through on news; realized loss may exceed VaR.",
                "Liquidity may prevent exit at the modelled stop.",
            ),
        )
