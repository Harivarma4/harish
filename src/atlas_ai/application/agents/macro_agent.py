"""Macro agent — a top-down read of the macroeconomic backdrop for equities.

Assesses rates, inflation, growth, bond yields, currency, oil, FII flows, and
global markets, and contributes a market-wide macro score/signals to the
recommendation. It fetches its snapshot through the injected ``MacroPort``.
"""

from __future__ import annotations

from atlas_ai.application.agents.base import AgentContext
from atlas_ai.application.ports.macro import MacroPort
from atlas_ai.domain.analysis import AgentReport, Signal
from atlas_ai.domain.enums import AgentKind, SignalStrength
from atlas_ai.domain.macro import MacroIndicators
from atlas_ai.domain.value_objects import Score

_SCALE = (
    SignalStrength.STRONG_BEARISH,
    SignalStrength.BEARISH,
    SignalStrength.NEUTRAL,
    SignalStrength.BULLISH,
    SignalStrength.STRONG_BULLISH,
)


def _grade(
    value: float, thresholds: tuple[float, float, float, float], *, higher_is_better: bool
) -> SignalStrength:
    """Map a value to a signal using ascending raw thresholds."""
    t0, t1, t2, t3 = thresholds
    rank = 0 if value < t0 else 1 if value < t1 else 2 if value < t2 else 3 if value < t3 else 4
    scale = _SCALE if higher_is_better else _SCALE[::-1]
    return scale[rank]


def _sig(
    name: str,
    value: float,
    thresholds: tuple[float, float, float, float],
    higher_is_better: bool,
    detail: str,
) -> Signal:
    return Signal(name, _grade(value, thresholds, higher_is_better=higher_is_better), detail, value)


class MacroAgent:
    """Computes a macro backdrop score from the current snapshot."""

    kind = AgentKind.MACRO

    def __init__(self, macro: MacroPort) -> None:
        self._macro = macro

    def analyze(self, ctx: AgentContext) -> AgentReport:
        m = self._macro.get_snapshot()
        signals = self._signals(m)

        bias = sum(s.directional_score for s in signals) / len(signals)
        score = Score(round((bias + 1.0) * 50.0, 2))
        rationale = (
            f"Repo {m.repo_rate_pct:.2f}%, CPI {m.cpi_inflation_pct:.1f}%, "
            f"GDP {m.gdp_growth_pct:.1f}%, 10Y {m.india_10y_yield_pct:.2f}%, "
            f"USDINR {m.usd_inr:.2f}, Brent ${m.crude_oil_usd:.0f}, "
            f"FII {m.fii_flow_cr:+.0f} cr, global {m.global_equity_trend_pct:+.1f}% "
            f"(as of {m.as_of})."
        )
        return AgentReport(
            agent=self.kind,
            score=score,
            signals=tuple(signals),
            rationale=rationale,
            assumptions=(
                "Macro snapshot is current and applies market-wide.",
                "Sector-specific sensitivities to macro are not modelled here.",
            ),
            risks=(
                "Policy surprises (RBI/Fed) can re-rate the whole market quickly.",
                "Oil and currency shocks can swing inflation and FII flows.",
                "Global risk-off episodes propagate to Indian equities.",
            ),
        )

    def _signals(self, m: MacroIndicators) -> list[Signal]:
        return [
            _sig("RepoRate", m.repo_rate_pct, (5.5, 6.0, 6.5, 7.0), False,
                 "RBI policy rate (lower is easier)"),
            _sig("Inflation", m.cpi_inflation_pct, (4.0, 5.0, 6.0, 7.0), False,
                 "Headline CPI YoY"),
            _sig("GDPGrowth", m.gdp_growth_pct, (5.0, 6.0, 7.0, 8.0), True,
                 "Real GDP growth YoY"),
            _sig("Bond10Y", m.india_10y_yield_pct, (6.5, 6.8, 7.2, 7.6), False,
                 "10Y g-sec yield (lower is supportive)"),
            _sig("Rupee", m.usd_inr, (82.0, 84.0, 86.0, 88.0), False,
                 "USDINR (stronger rupee is supportive)"),
            _sig("Crude", m.crude_oil_usd, (70.0, 80.0, 90.0, 100.0), False,
                 "Brent crude USD/bbl (lower is better for India)"),
            _sig("FIIFlow", m.fii_flow_cr, (-3000.0, -1000.0, 1000.0, 3000.0), True,
                 "Net FII equity flow, crores"),
            _sig("GlobalTrend", m.global_equity_trend_pct, (-3.0, -1.0, 1.0, 3.0), True,
                 "Recent global equity trend, %"),
        ]
