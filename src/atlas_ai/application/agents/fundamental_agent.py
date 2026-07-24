"""Fundamental analysis agent — scores quality, valuation, growth, and balance sheet."""

from __future__ import annotations

from atlas_ai.application.agents.base import AgentContext
from atlas_ai.domain.analysis import AgentReport, Signal
from atlas_ai.domain.enums import AgentKind, SignalStrength
from atlas_ai.domain.market import Fundamentals
from atlas_ai.domain.value_objects import Score


def _band(value: float, thresholds: tuple[float, float, float, float]) -> SignalStrength:
    """Map a value to a signal using ascending thresholds (bearish→bullish)."""
    t0, t1, t2, t3 = thresholds
    if value < t0:
        return SignalStrength.STRONG_BEARISH
    if value < t1:
        return SignalStrength.BEARISH
    if value < t2:
        return SignalStrength.NEUTRAL
    if value < t3:
        return SignalStrength.BULLISH
    return SignalStrength.STRONG_BULLISH


class FundamentalAgent:
    """Computes real fundamental signals and a 0..100 quality/valuation score."""

    kind = AgentKind.FUNDAMENTAL

    def analyze(self, ctx: AgentContext) -> AgentReport:
        f = ctx.fundamentals
        signals = self._signals(f)

        # Score = mean of the signals' [-1,1] bias mapped onto [0,100].
        bias = sum(s.directional_score for s in signals) / len(signals)
        score = Score(round((bias + 1.0) * 50.0, 2))

        peg_text = f"{f.peg}" if f.peg is not None else "n/a (non-positive growth)"
        rationale = (
            f"ROE {f.roe_pct:.1f}%, ROCE {f.roce_pct:.1f}%, D/E {f.debt_to_equity:.2f}, "
            f"net margin {f.net_margin_pct:.1f}%, P/E {f.pe:.1f}, PEG {peg_text}, "
            f"earnings growth {f.earnings_growth_pct:.1f}%."
        )
        assumptions = (
            "Reported fundamentals are accurate and comparable period-over-period.",
            "No undisclosed related-party or off-balance-sheet exposure.",
        )
        risks = self._risks(f)
        return AgentReport(
            agent=self.kind,
            score=score,
            signals=tuple(signals),
            rationale=rationale,
            assumptions=assumptions,
            risks=tuple(risks),
        )

    def _signals(self, f: Fundamentals) -> list[Signal]:
        peg = f.peg if f.peg is not None else 3.0
        return [
            Signal("ROE", _band(f.roe_pct, (8, 12, 15, 20)), "Return on equity", f.roe_pct),
            Signal(
                "ROCE", _band(f.roce_pct, (8, 12, 16, 22)), "Return on capital employed",
                f.roce_pct,
            ),
            Signal(
                "Debt/Equity",
                _band(-f.debt_to_equity, (-1.5, -1.0, -0.5, -0.2)),
                "Leverage (lower is better)",
                f.debt_to_equity,
            ),
            Signal(
                "NetMargin", _band(f.net_margin_pct, (3, 6, 10, 15)), "Net profit margin",
                f.net_margin_pct,
            ),
            Signal(
                "EarningsGrowth",
                _band(f.earnings_growth_pct, (0, 8, 15, 25)),
                "YoY earnings growth",
                f.earnings_growth_pct,
            ),
            Signal(
                "PEG",
                _band(-peg, (-2.5, -1.5, -1.0, -0.5)),
                "Valuation vs growth (lower is better)",
                peg,
            ),
        ]

    def _risks(self, f: Fundamentals) -> list[str]:
        risks: list[str] = []
        if f.debt_to_equity > 1.0:
            risks.append(f"Elevated leverage (D/E {f.debt_to_equity:.2f}).")
        if f.promoter_pledge_pct > 0:
            risks.append(f"Promoter pledging at {f.promoter_pledge_pct:.1f}%.")
        if f.pe > 40:
            risks.append(f"Rich valuation (P/E {f.pe:.1f}) leaves little margin of safety.")
        if not risks:
            risks.append("No red flags detected in the supplied fundamentals.")
        return risks
