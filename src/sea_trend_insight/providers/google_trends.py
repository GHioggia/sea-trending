from __future__ import annotations

import logging

import feedparser

from sea_trend_insight.models import SourceItem
from sea_trend_insight.providers.base import TrendProvider
from sea_trend_insight.providers.http_util import build_session, DEFAULT_TIMEOUT

log = logging.getLogger("sea_trend_insight")

COUNTRY_GEO = {"PH": "PH", "ID": "ID", "TH": "TH"}


class GoogleTrendsProvider(TrendProvider):
    name = "google_trends"
    platform = "google"

    def __init__(self, timeout: int = DEFAULT_TIMEOUT, proxy: str | None = None):
        self.timeout = timeout
        self.session = build_session(proxy=proxy)

    def fetch(self, country: str, date: str) -> list[SourceItem]:
        geo = COUNTRY_GEO.get(country)
        if not geo:
            log.warning("google_trends: unsupported country %s", country)
            return []

        url = f"https://trends.google.com/trending/rss?geo={geo}"
        resp = self.session.get(url, timeout=self.timeout)
        resp.raise_for_status()
        return self._parse(resp.text, country)

    def _parse(self, xml_text: str, country: str) -> list[SourceItem]:
        feed = feedparser.parse(xml_text)
        items: list[SourceItem] = []
        for i, entry in enumerate(feed.entries[:20]):
            title = entry.get("title", "")
            link = entry.get("link", "")
            published = entry.get("published", "")
            traffic = entry.get("ht_approx_traffic",
                                entry.get("approximate_traffic", ""))

            items.append(SourceItem(
                source=self.name,
                platform=self.platform,
                country=country,
                title=title,
                keyword=title,
                url=link,
                published_at=published,
                raw_score=self._parse_traffic(traffic),
                tags=["search", "trending"],
                summary=f"Search volume: {traffic}" if traffic else None,
            ))
        return items

    @staticmethod
    def _parse_traffic(v: str) -> float:
        v = v.strip().replace(",", "").replace("+", "").upper()
        if not v:
            return 0.0
        try:
            if v.endswith("K"):
                return float(v[:-1]) * 1_000
            if v.endswith("M"):
                return float(v[:-1]) * 1_000_000
            return float(v)
        except ValueError:
            return 0.0
