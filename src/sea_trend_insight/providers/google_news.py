from __future__ import annotations

import logging
from datetime import datetime, timezone

import feedparser

from sea_trend_insight.models import SourceItem
from sea_trend_insight.providers.base import TrendProvider
from sea_trend_insight.providers.http_util import build_session, DEFAULT_TIMEOUT

log = logging.getLogger("sea_trend_insight")

COUNTRY_FEED = {
    "PH": {"hl": "en-PH", "gl": "PH", "ceid": "PH:en"},
    "ID": {"hl": "id",    "gl": "ID", "ceid": "ID:id"},
    "TH": {"hl": "th",    "gl": "TH", "ceid": "TH:th"},
}


class GoogleNewsProvider(TrendProvider):
    name = "google_news"
    platform = "google"

    def __init__(self, timeout: int = DEFAULT_TIMEOUT, proxy: str | None = None):
        self.timeout = timeout
        self.session = build_session(proxy=proxy)

    def fetch(self, country: str, date: str) -> list[SourceItem]:
        params = COUNTRY_FEED.get(country)
        if not params:
            log.warning("google_news: unsupported country %s", country)
            return []

        url = (
            f"https://news.google.com/rss"
            f"?hl={params['hl']}&gl={params['gl']}&ceid={params['ceid']}"
        )
        resp = self.session.get(url, timeout=self.timeout)
        resp.raise_for_status()
        return self._parse(resp.text, country)

    def _parse(self, xml_text: str, country: str) -> list[SourceItem]:
        feed = feedparser.parse(xml_text)
        items: list[SourceItem] = []
        for i, entry in enumerate(feed.entries[:25]):
            title = entry.get("title", "")
            link = entry.get("link", "")
            published = entry.get("published", "")
            source_name = ""
            if hasattr(entry, "source"):
                source_name = entry.source.get("title", "")
            summary = entry.get("summary", entry.get("description", ""))
            if " - " in title and source_name:
                title = title.rsplit(" - ", 1)[0].strip()

            items.append(SourceItem(
                source=self.name,
                platform=self.platform,
                country=country,
                title=title,
                keyword=title[:80],
                url=link,
                published_at=published,
                raw_score=float(25 - i),
                language=COUNTRY_FEED.get(country, {}).get("hl", "en"),
                tags=["news"],
                summary=summary[:200] if summary else None,
            ))
        return items
