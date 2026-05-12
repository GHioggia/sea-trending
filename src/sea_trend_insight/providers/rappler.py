from __future__ import annotations

import logging
import re

import feedparser

from sea_trend_insight.models import SourceItem
from sea_trend_insight.providers.base import TrendProvider
from sea_trend_insight.providers.http_util import build_session, DEFAULT_TIMEOUT

log = logging.getLogger("sea_trend_insight")

FEEDS = [
    "https://www.rappler.com/feed/",
    "https://www.rappler.com/philippines/feed/",
]


class RapplerProvider(TrendProvider):
    name = "rappler"
    platform = "web"

    def __init__(self, timeout: int = DEFAULT_TIMEOUT, proxy: str | None = None):
        self.timeout = timeout
        self.session = build_session(proxy=proxy)

    def fetch(self, country: str, date: str) -> list[SourceItem]:
        if country != "PH":
            return []

        seen: set[str] = set()
        items: list[SourceItem] = []

        for feed_url in FEEDS:
            try:
                resp = self.session.get(feed_url, timeout=self.timeout)
                resp.raise_for_status()
                items.extend(self._parse(resp.text, country, seen))
            except Exception as exc:
                log.warning("rappler: failed to fetch %s: %s", feed_url, exc)

        return items[:25]

    def _parse(self, xml_text: str, country: str, seen: set[str]) -> list[SourceItem]:
        feed = feedparser.parse(xml_text)
        items: list[SourceItem] = []
        for entry in feed.entries:
            title = entry.get("title", "")
            link = entry.get("link", "")
            if not title or link in seen:
                continue
            seen.add(link)
            published = entry.get("published", "")
            summary = entry.get("summary", entry.get("description", ""))
            summary = re.sub(r"<[^>]+>", " ", summary).strip() if summary else ""
            tags = [t.get("term", "") for t in entry.get("tags", [])]

            items.append(SourceItem(
                source=self.name,
                platform=self.platform,
                country=country,
                title=title,
                keyword=title[:80],
                url=link,
                published_at=published,
                raw_score=float(25 - len(items)),
                language="en",
                tags=["news", "philippines"] + [t for t in tags[:3] if t],
                summary=summary[:200] if summary else None,
            ))
        return items
