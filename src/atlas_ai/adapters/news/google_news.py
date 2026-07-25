"""Real news adapter — public Google News RSS + a finance sentiment lexicon.

Google News publishes a free, key-less RSS search feed. This adapter queries it
per instrument, parses the headlines, scores each with a transparent finance
sentiment lexicon, and weights sources by reliability. It is a *simple* sentiment
model (a lexicon, not a transformer) — honest and deterministic; a learned NLP
model is a future upgrade.

Needs outbound access to ``news.google.com`` (firewalled in restricted
sandboxes). The HTTP client is injectable, so parsing/scoring are unit-tested
offline. A fetch failure returns an empty list (the news agent treats "no news"
as neutral) rather than failing the whole recommendation.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Protocol, runtime_checkable
from xml.etree import ElementTree  # nosec

from atlas_ai.application.ports.news import NewsItem
from atlas_ai.domain.market import Instrument

logger = logging.getLogger("atlas_ai.news")

_RSS = "https://news.google.com/rss/search"
_UA = "Mozilla/5.0 (compatible; AtlasAI/0.1; +research-tool)"

# Transparent finance sentiment lexicon (headline-level).
_POSITIVE = frozenset({
    "beats", "beat", "surge", "surges", "jumps", "gains", "rally", "rallies",
    "upgrade", "upgraded", "raises", "record", "profit", "growth", "wins",
    "order", "expansion", "strong", "outperform", "buy", "bullish", "rises",
    "high", "boost", "approval", "dividend",
})
_NEGATIVE = frozenset({
    "misses", "miss", "falls", "plunge", "plunges", "slump", "drops", "cut",
    "cuts", "downgrade", "downgraded", "loss", "losses", "probe", "fraud",
    "fine", "penalty", "weak", "underperform", "sell", "bearish", "decline",
    "declines", "concern", "concerns", "warning", "lawsuit", "recall", "default",
})

# Source reliability weights (substring match on the source name).
_RELIABILITY = {
    "reuters": 0.9, "bloomberg": 0.9, "cnbc": 0.75, "economic times": 0.75,
    "business standard": 0.75, "livemint": 0.75, "mint": 0.75,
    "moneycontrol": 0.7, "financial express": 0.7, "hindu businessline": 0.7,
    "ndtv profit": 0.65, "zee business": 0.6,
}


@runtime_checkable
class RssResponse(Protocol):
    @property
    def status_code(self) -> int: ...

    @property
    def text(self) -> str: ...


@runtime_checkable
class RssClient(Protocol):
    def get(self, url: str, *, params: dict[str, str], headers: dict[str, str]) -> RssResponse: ...


class HttpxRssClient:
    def __init__(self, *, timeout: float = 15.0) -> None:
        import httpx

        self._client = httpx.Client(timeout=timeout, headers={"User-Agent": _UA})

    def get(self, url: str, *, params: dict[str, str], headers: dict[str, str]) -> RssResponse:
        return self._client.get(url, params=params, headers=headers)


def _reliability(source: str) -> float:
    lowered = source.lower()
    for name, weight in _RELIABILITY.items():
        if name in lowered:
            return weight
    return 0.5


def _sentiment(text: str) -> float:
    tokens = [t.strip(".,:;!?()'\"").lower() for t in text.split()]
    pos = sum(1 for t in tokens if t in _POSITIVE)
    neg = sum(1 for t in tokens if t in _NEGATIVE)
    if pos + neg == 0:
        return 0.0
    return round((pos - neg) / (pos + neg), 3)


class GoogleNewsRSS:
    """Satisfies ``NewsPort`` using the public Google News RSS search feed."""

    def __init__(self, *, query_suffix: str = "share", client: RssClient | None = None) -> None:
        self._client = client if client is not None else HttpxRssClient()
        self._suffix = query_suffix

    def get_recent(self, instrument: Instrument, *, limit: int = 20) -> list[NewsItem]:
        query = f"{instrument.name or instrument.symbol} {self._suffix}".strip()
        params = {"q": query, "hl": "en-IN", "gl": "IN", "ceid": "IN:en"}
        try:
            resp = self._client.get(_RSS, params=params, headers={"User-Agent": _UA})
            if resp.status_code != 200:
                logger.warning("Google News HTTP %s for %s", resp.status_code, query)
                return []
            return self._parse(resp.text, limit)
        except Exception as exc:  # noqa: BLE001 - news must never break a recommendation
            logger.warning("Google News fetch failed for %s: %s", query, exc)
            return []

    def _parse(self, xml_text: str, limit: int) -> list[NewsItem]:
        try:
            root = ElementTree.fromstring(xml_text)  # nosec
        except ElementTree.ParseError as exc:
            logger.warning("Google News RSS parse error: %s", exc)
            return []
        items: list[NewsItem] = []
        for node in root.findall("./channel/item")[:limit]:
            headline = (node.findtext("title") or "").strip()
            if not headline:
                continue
            source_node = node.find("source")
            source = (source_node.text if source_node is not None and source_node.text else
                      "Google News")
            items.append(
                NewsItem(
                    headline=headline,
                    summary=(node.findtext("description") or headline).strip(),
                    source=source,
                    source_reliability=_reliability(source),
                    sentiment=_sentiment(headline),
                    published_at=_parse_date(node.findtext("pubDate")),
                    url=node.findtext("link"),
                )
            )
        return items


def _parse_date(raw: str | None) -> datetime:
    if raw:
        try:
            return parsedate_to_datetime(raw)
        except (TypeError, ValueError):
            pass
    return datetime.now(UTC)
