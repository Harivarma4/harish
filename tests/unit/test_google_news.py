"""GoogleNewsRSS adapter — offline via a fake RSS client."""

from __future__ import annotations

from atlas_ai.adapters.news.google_news import GoogleNewsRSS, _reliability, _sentiment
from atlas_ai.domain.enums import Exchange
from atlas_ai.domain.market import Instrument

INSTRUMENT = Instrument("RELIANCE", Exchange.NSE, "Reliance Industries")

_RSS_XML = """<?xml version="1.0"?>
<rss version="2.0"><channel>
  <item>
    <title>Reliance profit beats estimates, shares surge</title>
    <link>https://example.com/1</link>
    <pubDate>Wed, 14 Jan 2026 09:30:00 GMT</pubDate>
    <source url="https://reuters.com">Reuters</source>
    <description>Q3 profit up</description>
  </item>
  <item>
    <title>Reliance faces probe over margin pressure, stock falls</title>
    <link>https://example.com/2</link>
    <pubDate>Tue, 13 Jan 2026 06:00:00 GMT</pubDate>
    <source url="https://moneycontrol.com">Moneycontrol</source>
  </item>
</channel></rss>
"""


class FakeResp:
    def __init__(self, text: str, status_code: int = 200) -> None:
        self.text = text
        self.status_code = status_code


class FakeRss:
    def __init__(self, resp: FakeResp) -> None:
        self._resp = resp
        self.calls: list[dict[str, str]] = []

    def get(self, url: str, *, params: dict[str, str], headers: dict[str, str]) -> FakeResp:
        self.calls.append(params)
        return self._resp


def test_parses_headlines_source_and_sentiment() -> None:
    rss = FakeRss(FakeResp(_RSS_XML))
    items = GoogleNewsRSS(client=rss).get_recent(INSTRUMENT)
    assert len(items) == 2
    first, second = items
    assert "beats estimates" in first.headline
    assert first.source == "Reuters"
    assert first.source_reliability == 0.9
    assert first.sentiment > 0            # "beats" + "surge"
    assert second.sentiment < 0           # "probe" + "falls" + "pressure"?
    # query used the company name
    assert "Reliance Industries" in rss.calls[0]["q"]


def test_http_error_returns_empty() -> None:
    items = GoogleNewsRSS(client=FakeRss(FakeResp("", status_code=503))).get_recent(INSTRUMENT)
    assert items == []


def test_malformed_xml_returns_empty() -> None:
    items = GoogleNewsRSS(client=FakeRss(FakeResp("<not-xml"))).get_recent(INSTRUMENT)
    assert items == []


def test_sentiment_and_reliability_helpers() -> None:
    assert _sentiment("profit surge gains") > 0
    assert _sentiment("loss plunge probe") < 0
    assert _sentiment("board meeting scheduled") == 0.0
    assert _reliability("The Economic Times") == 0.75
    assert _reliability("Unknown Blog") == 0.5
