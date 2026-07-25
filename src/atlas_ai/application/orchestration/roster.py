"""Static role/responsibility profiles for every agent in the system.

This is the authoritative, human-readable description of what each specialist
does. The orchestrator merges these profiles with live configuration (data
source authenticity and blend weight) to answer "which agents are live, on what
data, and doing what?".
"""

from __future__ import annotations

from dataclasses import dataclass

from atlas_ai.domain.enums import AgentKind


@dataclass(frozen=True, slots=True)
class AgentProfile:
    """What an agent is for — its role and concrete responsibilities."""

    role: str
    responsibilities: tuple[str, ...]


AGENT_PROFILES: dict[AgentKind, AgentProfile] = {
    AgentKind.FUNDAMENTAL: AgentProfile(
        role="Bottom-up business quality & valuation",
        responsibilities=(
            "Score ROE/ROCE, margins, leverage, growth, and PE/PEG.",
            "Flag balance-sheet quality and valuation extremes.",
        ),
    ),
    AgentKind.TECHNICAL: AgentProfile(
        role="Price-action & trend read",
        responsibilities=(
            "Compute SMA/EMA/RSI/MACD/ATR from the candle series.",
            "Assess trend, momentum, and volatility state.",
        ),
    ),
    AgentKind.QUANT: AgentProfile(
        role="Cross-sectional factor exposure",
        responsibilities=(
            "Derive momentum, low-vol, mean-reversion, quality, value factors.",
            "Blend factors into a single quantitative tilt.",
        ),
    ),
    AgentKind.MACRO: AgentProfile(
        role="Top-down macro backdrop",
        responsibilities=(
            "Read rates, inflation, growth, yields, currency, oil, FII flows.",
            "Overlay a market-wide macro regime on bottom-up views.",
        ),
    ),
    AgentKind.NEWS: AgentProfile(
        role="News sentiment & flow",
        responsibilities=(
            "Score recent headlines with a finance sentiment lexicon.",
            "Weight sentiment by source reliability.",
        ),
    ),
    AgentKind.BEHAVIORAL: AgentProfile(
        role="Crowd psychology (contrarian)",
        responsibilities=(
            "Gauge fear/greed, volatility regime, and volume herding.",
            "Lean contrarian at sentiment extremes.",
        ),
    ),
    AgentKind.OPTIONS: AgentProfile(
        role="Derivatives positioning",
        responsibilities=(
            "Read PCR, max-pain, and IV skew from the option chain.",
            "Compute ATM Greeks with Black-Scholes.",
        ),
    ),
    AgentKind.PORTFOLIO: AgentProfile(
        role="Portfolio construction & fit",
        responsibilities=(
            "Measure book concentration (HHI) and sector exposure.",
            "Judge whether the candidate diversifies or concentrates.",
        ),
    ),
    AgentKind.MEMORY: AgentProfile(
        role="Institutional memory",
        responsibilities=(
            "Recall prior stances on the instrument (recency-weighted).",
            "Reward view persistence; flag flip-flops (low weight).",
        ),
    ),
    AgentKind.LEARNING: AgentProfile(
        role="Instrument-specific calibration",
        responsibilities=(
            "Walk-forward backtest a trend rule on the instrument's history.",
            "Report hit-rate/Sharpe and gate the live reading on edge.",
        ),
    ),
    AgentKind.RISK: AgentProfile(
        role="Risk sizing & downside",
        responsibilities=(
            "Derive position size, VaR, ATR-based stop, and reward:risk.",
            "Bound conviction with an explicit downside plan.",
        ),
    ),
    AgentKind.DEBATE: AgentProfile(
        role="Adversarial synthesis (bull/bear/judge)",
        responsibilities=(
            "Argue both sides over all reports via the LLM port.",
            "Produce a balanced verdict and leaning.",
        ),
    ),
    AgentKind.EVIDENCE: AgentProfile(
        role="Evidence assembly & caveats",
        responsibilities=(
            "Attribute supporting/counter evidence to sources.",
            "Surface catalysts, counter-arguments, and unknown risks.",
        ),
    ),
}
