"""Debate agent — bull vs. bear, reconciled by a judge, before any recommendation."""

from __future__ import annotations

from atlas_ai.application.agents.base import AgentContext
from atlas_ai.application.ports.llm import LLMPort
from atlas_ai.domain.analysis import AgentReport
from atlas_ai.domain.debate import DebateArgument, DebateOutcome
from atlas_ai.domain.enums import SignalStrength


class DebateAgent:
    """Constructs the bull and bear cases from the reports and has a judge rule.

    The numeric ``leaning`` is grounded in the specialists' scores; the narrative
    (theses and verdict) is produced through the LLM port so it is explainable.
    """

    def __init__(self, llm: LLMPort, *, prompt_version: str = "debate-v1") -> None:
        self.llm = llm
        self.prompt_version = prompt_version

    def debate(self, ctx: AgentContext, reports: list[AgentReport]) -> DebateOutcome:
        bull_points = self._points(reports, bullish=True)
        bear_points = self._points(reports, bullish=False)

        # Leaning: mean of each report's score mapped from [0,100] to [-1,1].
        leaning = sum(r.score.as_unit() * 2.0 - 1.0 for r in reports) / len(reports)

        symbol = ctx.instrument.symbol
        bull_text = self.llm.complete(
            f"Argue the BULL case for {symbol} in one sentence given: "
            + "; ".join(bull_points),
            system="You are a disciplined buy-side analyst making the constructive case.",
            prompt_version=self.prompt_version,
        ).text
        bear_text = self.llm.complete(
            f"Argue the BEAR case for {symbol} in one sentence given: "
            + "; ".join(bear_points),
            system="You are a skeptical risk manager making the cautionary case.",
            prompt_version=self.prompt_version,
        ).text
        verdict = self.llm.complete(
            f"As an impartial judge, reconcile the bull and bear cases for {symbol}. "
            f"Net analytical leaning is {leaning:+.2f} on [-1,1]. Give a one-sentence verdict.",
            system="You are an impartial investment-committee chair.",
            prompt_version=self.prompt_version,
        ).text

        return DebateOutcome(
            bull=DebateArgument("BULL", bull_text, tuple(bull_points)),
            bear=DebateArgument("BEAR", bear_text, tuple(bear_points)),
            verdict=verdict,
            leaning=round(max(-1.0, min(1.0, leaning)), 4),
        )

    def _points(self, reports: list[AgentReport], *, bullish: bool) -> list[str]:
        wanted = (
            {SignalStrength.BULLISH, SignalStrength.STRONG_BULLISH}
            if bullish
            else {SignalStrength.BEARISH, SignalStrength.STRONG_BEARISH}
        )
        points = [
            f"{r.agent.value}:{s.name}={s.value}"
            for r in reports
            for s in r.signals
            if s.strength in wanted
        ]
        if not points:
            points.append(
                "no strongly supportive signals" if bullish else "no material red flags"
            )
        return points
