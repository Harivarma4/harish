"""News-sentiment agent — reliability-weighted sentiment from recent coverage.

Aggregates recent, sentiment-scored news for the instrument (fetched through the
injected ``NewsPort``) into a market-facing sentiment signal, weighting each item
by its source's reliability so a Reuters headline counts for more than a social
post.
"""

from __future__ import annotations

from atlas_ai.application.agents.base import AgentContext
from atlas_ai.application.ports.news import NewsItem, NewsPort
from atlas_ai.domain.analysis import AgentReport, Signal
from atlas_ai.domain.enums import AgentKind, SignalStrength
from atlas_ai.domain.value_objects import Score

_FETCH_LIMIT = 15
_RECENT_WINDOW = 3


def _strength(sentiment: float) -> SignalStrength:
    if sentiment >= 0.5:
        return SignalStrength.STRONG_BULLISH
    if sentiment >= 0.15:
        return SignalStrength.BULLISH
    if sentiment > -0.15:
        return SignalStrength.NEUTRAL
    if sentiment > -0.5:
        return SignalStrength.BEARISH
    return SignalStrength.STRONG_BEARISH


class NewsAgent:
    """Turns recent news into a reliability-weighted sentiment report."""

    kind = AgentKind.NEWS

    def __init__(self, news: NewsPort) -> None:
        self._news = news

    def analyze(self, ctx: AgentContext) -> AgentReport:
        items = self._news.get_recent(ctx.instrument, limit=_FETCH_LIMIT)
        if not items:
            return self._empty_report()

        net = _weighted_sentiment(items)
        recent = sorted(items, key=lambda i: i.published_at, reverse=True)[:_RECENT_WINDOW]
        recent_mean = sum(i.sentiment for i in recent) / len(recent)
        avg_reliability = sum(i.source_reliability for i in items) / len(items)

        signals = (
            Signal("NetSentiment", _strength(net), "Reliability-weighted sentiment", round(net, 3)),
            Signal("RecentTilt", _strength(recent_mean), "Sentiment of the latest items",
                   round(recent_mean, 3)),
            Signal("Coverage", SignalStrength.NEUTRAL, "Number of items analyzed",
                   float(len(items))),
        )
        bias = sum(s.directional_score for s in signals) / len(signals)
        score = Score(round((bias + 1.0) * 50.0, 2))

        top = max(items, key=lambda i: abs(i.sentiment) * i.source_reliability)
        rationale = (
            f"{len(items)} items, net sentiment {net:+.2f} (avg source reliability "
            f"{avg_reliability:.2f}); most salient: \"{top.headline}\" ({top.source})."
        )
        return AgentReport(
            agent=self.kind,
            score=score,
            signals=signals,
            rationale=rationale,
            assumptions=(
                "Sentiment scores and source reliabilities are accurate.",
                "Coverage is representative and not manipulated.",
            ),
            risks=(
                "Headline sentiment can be noisy and reverse quickly.",
                "Low-reliability or coordinated sources can skew the read.",
            ),
        )

    def _empty_report(self) -> AgentReport:
        return AgentReport(
            agent=self.kind,
            score=Score(50.0),
            signals=(Signal("Coverage", SignalStrength.NEUTRAL, "No recent news found", 0.0),),
            rationale="No recent news found for this instrument.",
            assumptions=("Absence of news is treated as neutral, not bullish or bearish.",),
            risks=("Missing coverage may hide material developments.",),
        )


def _weighted_sentiment(items: list[NewsItem]) -> float:
    total_weight = sum(i.source_reliability for i in items)
    if total_weight == 0:
        return 0.0
    return sum(i.sentiment * i.source_reliability for i in items) / total_weight
