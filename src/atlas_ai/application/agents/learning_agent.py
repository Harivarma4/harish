"""Learning agent — instrument-specific calibration from a self-backtest.

Runs a simple, transparent walk-forward backtest of a long-only trend rule
(close above its SMA, held forward a fixed horizon) over the candles already in
context, and reports whether that rule has had *edge on this instrument*:

- **BacktestHitRate** — share of historical trades with a positive forward return.
- **BacktestSharpe** — per-trade mean/│std│, a consistency (reliability) read.
- **LiveRuleSignal** — the current rule reading, but only actionable when the
  backtest shows edge; a rule with no historical edge contributes nothing.

The backtest is in-sample on one series (instrument-specific calibration, not a
cross-sectional strategy claim) and uses only information available up to each
decision point — no look-ahead beyond the labelled forward horizon.
"""

from __future__ import annotations

import statistics

from atlas_ai.application.agents.base import AgentContext
from atlas_ai.application.agents.indicators import sma
from atlas_ai.domain.analysis import AgentReport, Signal
from atlas_ai.domain.enums import AgentKind, SignalStrength
from atlas_ai.domain.value_objects import Score

_SCALE = (
    SignalStrength.STRONG_BEARISH,
    SignalStrength.BEARISH,
    SignalStrength.NEUTRAL,
    SignalStrength.BULLISH,
    SignalStrength.STRONG_BULLISH,
)


def _grade(value: float, thresholds: tuple[float, float, float, float]) -> SignalStrength:
    t0, t1, t2, t3 = thresholds
    rank = 0 if value < t0 else 1 if value < t1 else 2 if value < t2 else 3 if value < t3 else 4
    return _SCALE[rank]


class LearningAgent:
    """Calibrates conviction from an instrument-specific self-backtest."""

    kind = AgentKind.LEARNING

    def __init__(self, *, sma_period: int = 20, horizon: int = 5) -> None:
        self._sma_period = sma_period
        self._horizon = horizon

    def analyze(self, ctx: AgentContext) -> AgentReport:
        closes = [c.close for c in ctx.candles]
        trades = self._backtest(closes)
        if len(trades) < 10:
            return self._insufficient_report(len(trades))

        hit_rate = sum(1 for r in trades if r > 0.0) / len(trades)
        mean_ret = statistics.fmean(trades)
        spread = statistics.pstdev(trades) or 1e-9
        sharpe = mean_ret / spread

        signals = (
            Signal("BacktestHitRate", _grade(hit_rate, (0.45, 0.5, 0.55, 0.6)),
                   "Share of historical trend trades that paid off", round(hit_rate, 3)),
            Signal("BacktestSharpe", _grade(sharpe, (-0.1, 0.0, 0.1, 0.25)),
                   "Per-trade mean/std of the trend rule (reliability)", round(sharpe, 3)),
            self._live_signal(closes, mean_ret),
        )
        bias = sum(s.directional_score for s in signals) / len(signals)
        score = Score(round((bias + 1.0) * 50.0, 2))
        rationale = (
            f"Trend rule (close>SMA{self._sma_period}, {self._horizon}d fwd) over "
            f"{len(trades)} trades: hit-rate {hit_rate * 100:.0f}%, avg fwd "
            f"{mean_ret * 100:+.2f}%, Sharpe {sharpe:.2f}. "
            f"Currently {'engaged (long)' if self._is_long(closes) else 'flat'}."
        )
        return AgentReport(
            agent=self.kind,
            score=score,
            signals=signals,
            rationale=rationale,
            assumptions=(
                "Past rule behaviour on this instrument is informative for calibration.",
                "Costs/slippage are ignored; the backtest measures raw edge.",
            ),
            risks=(
                "In-sample on a single series; edge can be regime-specific and fade.",
                "A short history gives noisy hit-rate and Sharpe estimates.",
            ),
        )

    def _backtest(self, closes: list[float]) -> list[float]:
        trades: list[float] = []
        last = len(closes) - self._horizon
        for t in range(self._sma_period, last):
            baseline = sma(closes[: t + 1], self._sma_period)
            if baseline is None or closes[t] <= baseline:
                continue  # long-only: rule engaged only above the SMA
            entry = closes[t]
            if entry <= 0.0:
                continue
            trades.append((closes[t + self._horizon] - entry) / entry)
        return trades

    def _live_signal(self, closes: list[float], mean_ret: float) -> Signal:
        # Only actionable when the backtest shows a positive historical edge and
        # the rule is currently engaged; otherwise it says nothing directional.
        if not self._is_long(closes) or mean_ret <= 0.0:
            return Signal("LiveRuleSignal", SignalStrength.NEUTRAL,
                          "Trend rule flat or without historical edge", 0.0)
        strength = _grade(mean_ret * 100.0, (-1.0, 0.0, 1.0, 2.0))
        return Signal("LiveRuleSignal", strength,
                      "Current rule reading, weighted by its backtested edge",
                      round(mean_ret * 100.0, 2))

    def _is_long(self, closes: list[float]) -> bool:
        baseline = sma(closes, self._sma_period)
        return baseline is not None and closes[-1] > baseline

    def _insufficient_report(self, n_trades: int) -> AgentReport:
        return AgentReport(
            agent=self.kind,
            score=Score(50.0),
            signals=(
                Signal("BacktestHitRate", SignalStrength.NEUTRAL,
                       "Insufficient history to backtest the trend rule", float(n_trades)),
            ),
            rationale="Not enough price history to calibrate a trend rule on this instrument.",
            assumptions=("A reliable backtest needs a longer candle history.",),
            risks=("Without calibration the model leans on its untuned priors.",),
        )
