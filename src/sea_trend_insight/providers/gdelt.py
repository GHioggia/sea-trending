from __future__ import annotations

import logging

from sea_trend_insight.models import SourceItem
from sea_trend_insight.providers.base import TrendProvider
from sea_trend_insight.providers.http_util import build_session, DEFAULT_TIMEOUT

log = logging.getLogger("sea_trend_insight")

COUNTRY_QUERY = {
    "PH": "sourcecountry:Philippines",
    "ID": "sourcecountry:Indonesia",
    "TH": "sourcecountry:Thailand",
}
COUNTRY_LANG = {"PH": "English", "ID": "Indonesian", "TH": "Thai"}
API_URL = "https://api.gdeltproject.org/api/v2/doc/doc"


class GdeltProvider(TrendProvider):
    name = "gdelt"
    platform = "gdelt"

    def __init__(self, timeout: int = DEFAULT_TIMEOUT, max_records: int = 30, proxy: str | None = None):
        self.timeout = timeout
        self.max_records = max_records
        self.session = build_session(proxy=proxy)

    def fetch(self, country: str, date: str) -> list[SourceItem]:
        query = COUNTRY_QUERY.get(country)
        if not query:
            log.warning("gdelt: unsupported country %s", country)
            return []

        params = {
            "query": query,
            "mode": "artlist",
            "format": "json",
            "maxrecords": str(self.max_records),
            "sort": "DateDesc",
        }
        resp = self.session.get(API_URL, params=params, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        return self._parse(data, country)

    def _parse(self, data: dict, country: str) -> list[SourceItem]:
        articles = data.get("articles", [])
        items: list[SourceItem] = []
        for i, art in enumerate(articles):
            title = art.get("title", "")
            url = art.get("url", "")
            seen = art.get("seendate", "")
            domain = art.get("domain", "")
            lang = art.get("language", COUNTRY_LANG.get(country, ""))

            items.append(SourceItem(
                source=self.name,
                platform=self.platform,
                country=country,
                title=title,
                keyword=title[:80],
                url=url,
                published_at=seen,
                raw_score=float(len(articles) - i),
                language=lang.lower()[:2] if lang else None,
                tags=["news", domain] if domain else ["news"],
                summary=None,
            ))
        return items
