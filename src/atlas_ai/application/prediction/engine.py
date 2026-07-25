"""Probabilistic forecasting: Bayesian score blend + Monte Carlo simulation.

Deliberately emits *no* point prediction. The blended agent scores set a
regularized prior (a Beta update); a seeded Monte Carlo over the return
distribution yields the probability of a favourable outcome and a CAGR
distribution with a confidence interval. A fixed seed keeps every forecast
reproducible for audit.
"""

from __future__ import annotations

import numpy as np

from atlas_ai.application.agents.base import AgentContext
from atlas_ai.domain.analysis import AgentReport
from atlas_ai.domain.debate import DebateOutcome
from atlas_ai.domain.enums import AgentKind
from atlas_ai.domain.forecast import ProbabilisticOutlook
from atlas_ai.domain.value_objects import Confidence, Percent

# Relative weights when blending specialist scores into a single edge.
_WEIGHTS = {
    AgentKind.FUNDAMENTAL: 0.35,
    AgentKind.TECHNICAL: 0.25,
    AgentKind.MACRO: 0.15,
    AgentKind.NEWS: 0.10,
    AgentKind.RISK: 0.15,
}
# Strength of the Beta prior update (pseudo-observations). Higher = more shrinkage.
_KAPPA = 12.0
# Max absolute annual drift implied by a maximal edge.
_MAX_ANNUAL_DRIFT = 0.18


class PredictionEngine:
    def __init__(
        self, *, simulations: int = 10_000, seed: int = 42, trading_days: int = 252
    ) -> None:
        self.simulations = simulations
        self.seed = seed
        self.trading_days = trading_days

    def forecast(
        self,
        ctx: AgentContext,
        reports: list[AgentReport],
        debate: DebateOutcome,
        *,
        horizon_days: int,
    ) -> ProbabilisticOutlook:
        edge = self._blended_edge(reports, debate)          # unit [0, 1]
        posterior_mean = self._bayesian_probability(edge)   # regularized prior
        daily_sigma = self._daily_volatility(ctx)
        mu_annual = (2.0 * edge - 1.0) * _MAX_ANNUAL_DRIFT
        mu_daily = mu_annual / self.trading_days

        cagr = self._monte_carlo_cagr(mu_daily, daily_sigma, horizon_days)
        prob_favourable = float(np.mean(cagr > 0.0))
        # Blend the model-free MC probability with the regularized Bayesian prior.
        probability = 0.5 * prob_favourable + 0.5 * posterior_mean

        confidence = self._confidence(reports, len(ctx.candles))
        return ProbabilisticOutlook(
            probability_favourable=round(probability, 4),
            expected_cagr=Percent(round(float(np.mean(cagr)) * 100.0, 2)),
            cagr_p05=Percent(round(float(np.percentile(cagr, 5)) * 100.0, 2)),
            cagr_p95=Percent(round(float(np.percentile(cagr, 95)) * 100.0, 2)),
            confidence=confidence,
            simulations=self.simulations,
        )

    def _blended_edge(self, reports: list[AgentReport], debate: DebateOutcome) -> float:
        total_w = 0.0
        acc = 0.0
        for r in reports:
            w = _WEIGHTS.get(r.agent, 0.1)
            acc += w * r.score.as_unit()
            total_w += w
        score_edge = acc / total_w if total_w else 0.5
        # Fold in the debate leaning ([-1,1] -> [0,1]) with a small weight.
        debate_edge = (debate.leaning + 1.0) / 2.0
        edge = 0.8 * score_edge + 0.2 * debate_edge
        return float(min(max(edge, 0.0), 1.0))

    def _bayesian_probability(self, edge: float) -> float:
        # Beta(a, b) prior updated toward the edge; mean regularized toward 0.5.
        a = 1.0 + _KAPPA * edge
        b = 1.0 + _KAPPA * (1.0 - edge)
        return a / (a + b)

    def _daily_volatility(self, ctx: AgentContext) -> float:
        closes = np.array([c.close for c in ctx.candles], dtype=float)
        if closes.size < 3:
            return 0.02  # fallback ~2% daily
        returns = np.diff(closes) / closes[:-1]
        sigma = float(np.std(returns, ddof=1))
        return max(sigma, 1e-4)

    def _monte_carlo_cagr(
        self, mu_daily: float, sigma_daily: float, horizon_days: int
    ) -> np.ndarray:
        rng = np.random.default_rng(self.seed)
        steps = max(horizon_days, 1)
        # Geometric random walk: sum of daily log-ish returns per path.
        shocks = rng.normal(mu_daily, sigma_daily, size=(self.simulations, steps))
        terminal = np.prod(1.0 + shocks, axis=1)
        terminal = np.clip(terminal, 1e-6, None)
        years = steps / self.trading_days
        return terminal ** (1.0 / years) - 1.0

    def _confidence(self, reports: list[AgentReport], history_len: int) -> Confidence:
        # Agreement: tight cluster of scores -> more confident.
        units = np.array([r.score.as_unit() for r in reports], dtype=float)
        spread = float(np.std(units)) if units.size > 1 else 0.25
        agreement = max(0.0, 1.0 - spread * 2.0)
        # Data sufficiency: reward having enough history for the indicators.
        sufficiency = min(history_len / 200.0, 1.0)
        value = 0.2 + 0.55 * agreement + 0.25 * sufficiency
        return Confidence(round(min(max(value, 0.0), 0.95), 4))
