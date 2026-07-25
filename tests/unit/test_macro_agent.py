"""Macro agent scoring behaviour."""

from __future__ import annotations

from datetime import date

from atlas_ai.adapters.macro.mock_macro import MockMacro
from atlas_ai.application.agents.base import AgentContext
from atlas_ai.application.agents.macro_agent import MacroAgent
from atlas_ai.domain.enums import AgentKind, Exchange, SignalStrength
from atlas_ai.domain.macro import MacroIndicators
from atlas_ai.domain.market import Candle, Instrument, Quote
from tests.conftest import make_fundamentals


def _ctx() -> AgentContext:
    inst = Instrument("RELIANCE", Exchange.NSE)
    quote = Quote(inst, 100.0, 101.0, 99.0, 1_000_000)
    candle = Candle(date(2026, 1, 1), 100.0, 101.0, 99.0, 100.0, 1_000_000)
    # Fundamentals aren't used by the macro agent; a minimal stand-in is fine.
    return AgentContext(inst, quote, [candle], make_fundamentals(inst), 100_000.0)


def _macro(**overrides: float) -> MockMacro:
    base = dict(
        repo_rate_pct=6.5, cpi_inflation_pct=5.1, gdp_growth_pct=6.8,
        india_10y_yield_pct=7.0, usd_inr=84.5, crude_oil_usd=82.0,
        fii_flow_cr=-1500.0, global_equity_trend_pct=1.2,
    )
    base.update(overrides)
    return MockMacro(snapshot=MacroIndicators(as_of=date(2026, 1, 1), **base))  # type: ignore[arg-type]


def test_supportive_macro_outscores_hostile_macro() -> None:
    supportive = MacroAgent(_macro(
        repo_rate_pct=5.0, cpi_inflation_pct=3.5, gdp_growth_pct=8.5,
        india_10y_yield_pct=6.3, usd_inr=81.0, crude_oil_usd=65.0,
        fii_flow_cr=5000.0, global_equity_trend_pct=4.0,
    )).analyze(_ctx())
    hostile = MacroAgent(_macro(
        repo_rate_pct=7.5, cpi_inflation_pct=7.5, gdp_growth_pct=4.0,
        india_10y_yield_pct=7.8, usd_inr=89.0, crude_oil_usd=105.0,
        fii_flow_cr=-5000.0, global_equity_trend_pct=-4.0,
    )).analyze(_ctx())
    assert supportive.score.value > hostile.score.value
    assert supportive.agent is AgentKind.MACRO


def test_all_indicators_produce_signals() -> None:
    report = MacroAgent(_macro()).analyze(_ctx())
    names = {s.name for s in report.signals}
    assert names == {
        "RepoRate", "Inflation", "GDPGrowth", "Bond10Y",
        "Rupee", "Crude", "FIIFlow", "GlobalTrend",
    }
    assert report.assumptions and report.risks


def test_hostile_macro_flags_bearish_signals() -> None:
    report = MacroAgent(_macro(crude_oil_usd=110.0, fii_flow_cr=-8000.0)).analyze(_ctx())
    by_name = {s.name: s.strength for s in report.signals}
    assert by_name["Crude"] is SignalStrength.STRONG_BEARISH
    assert by_name["FIIFlow"] is SignalStrength.STRONG_BEARISH
