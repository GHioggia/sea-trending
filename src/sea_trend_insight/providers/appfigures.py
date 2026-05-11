from __future__ import annotations

import logging

from sea_trend_insight.models import SourceItem
from sea_trend_insight.providers.base import TrendProvider
from sea_trend_insight.providers.http_util import build_session, DEFAULT_TIMEOUT

log = logging.getLogger("sea_trend_insight")

BASE_URL = "https://api.appfigures.com/v2"


class AppfiguresProvider(TrendProvider):
    """Appfigures requires an API key. Returns empty if not configured."""
    name = "appfigures"
    platform = "appstore"

    def __init__(self, api_key: str | None = None, timeout: int = DEFAULT_TIMEOUT, proxy: str | None = None):
        self.api_key = api_key
        self.timeout = timeout
        self.session = build_session(proxy=proxy)

    def fetch(self, country: str, date: str) -> list[SourceItem]:
        if not self.api_key:
            log.info("appfigures: no API key configured, skipping")
            return []

        url = f"{BASE_URL}/ranks/google/games/free/country={country.lower()}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        resp = self.session.get(url, headers=headers, timeout=self.timeout)
        resp.raise_for_status()
        return self._parse(resp.json(), country)

    def _parse(self, data: list | dict, country: str) -> list[SourceItem]:
        entries = data if isinstance(data, list) else data.get("data", [])
        items: list[SourceItem] = []
        for i, entry in enumerate(entries[:20]):
            title = entry.get("name", entry.get("title", ""))
            if not title:
                continue
            items.append(SourceItem(
                source=self.name,
                platform=self.platform,
                country=country,
                title=title,
                keyword=title,
                url=entry.get("url"),
                raw_score=float(i + 1),
                tags=["app", "game", "ranking"],
                summary=entry.get("developer", {}).get("name"),
            ))
        return items
