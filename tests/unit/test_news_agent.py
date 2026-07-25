"""News-sentiment agent scoring behaviour."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from atlas_ai.adapters.news.mock_news import MockNews
from atlas_ai.application.agents.base import AgentContext
from atlas_ai.application.agents.news_agent import NewsAgent
from atlas_ai.application.ports.news import NewsItem
from atlas_ai.domain.enums import AgentKind, Exchange, SignalStrength
from atlas_ai.domain.market import Candle, Instrument, Quote
from tests.conftest import make_fundamentals

INSTRUMENT = Instrument("RELIANCE", Exchange.NSE)


def _ctx() -> AgentContext:
    quote = Quote(INSTRUMENT, 100.0, 101.0, 99.0, 1_000_000)
    candle = Candle(datetime(2026, 1, 1).date(), 100.0, 101.0, 99.0, 100.0, 1_000_000)
    return AgentContext(INSTRUMENT, quote, [candle], make_fundamentals(INSTRUMENT), 100_000.0)


class StaticNews:
    def __init__(self, items: list[NewsItem]) -> None:
        self._items = items

    def get_recent(self, instrument: Instrument, *, limit: int = 20) -> list[NewsItem]:
        return self._items[:limit]


def _item(sentiment: float, reliability: float, *, day: int = 0) -> NewsItem:
    return NewsItem(
        headline="RELIANCE update",
        summary="...",
        source="Reuters",
        source_reliability=reliability,
        sentiment=sentiment,
        published_at=datetime(2026, 1, 1, tzinfo=UTC) - timedelta(days=day),
    )


def test_positive_news_outscores_negative() -> None:
    pos_news = StaticNews([_item(0.8, 0.9), _item(0.6, 0.8), _item(0.7, 0.9)])
    neg_news = StaticNews([_item(-0.8, 0.9), _item(-0.6, 0.8), _item(-0.7, 0.9)])
    pos = NewsAgent(pos_news).analyze(_ctx())
    neg = NewsAgent(neg_news).analyze(_ctx())
    assert pos.score.value > neg.score.value
    assert pos.agent is AgentKind.NEWS


def test_reliability_weighting() -> None:
    # A strong-negative but low-reliability item shouldn't flip a reliable-positive set.
    items = [_item(0.7, 0.9), _item(0.6, 0.9), _item(-0.9, 0.2)]
    report = NewsAgent(StaticNews(items)).analyze(_ctx())
    net = next(s for s in report.signals if s.name == "NetSentiment")
    assert net.value is not None and net.value > 0  # stays net-positive


def test_no_news_is_neutral() -> None:
    report = NewsAgent(StaticNews([])).analyze(_ctx())
    assert report.score.value == 50.0
    assert report.signals[0].strength is SignalStrength.NEUTRAL


def test_mock_news_is_deterministic() -> None:
    a = MockNews().get_recent(INSTRUMENT)
    b = MockNews().get_recent(INSTRUMENT)
    assert [i.headline for i in a] == [i.headline for i in b]
    assert all(-1.0 <= i.sentiment <= 1.0 for i in a)
