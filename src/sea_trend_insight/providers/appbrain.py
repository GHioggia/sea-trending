from __future__ import annotations

import logging

from bs4 import BeautifulSoup

from sea_trend_insight.models import SourceItem
from sea_trend_insight.providers.base import TrendProvider
from sea_trend_insight.providers.http_util import build_session, DEFAULT_TIMEOUT

log = logging.getLogger("sea_trend_insight")

COUNTRY_CODE = {"PH": "ph", "ID": "id", "TH": "th"}
BASE_URL = "https://www.appbrain.com"


class AppBrainProvider(TrendProvider):
    name = "appbrain"
    platform = "android"

    def __init__(self, timeout: int = DEFAULT_TIMEOUT, proxy: str | None = None):
        self.timeout = timeout
        self.session = build_session(proxy=proxy)

    def fetch(self, country: str, date: str) -> list[SourceItem]:
        cc = COUNTRY_CODE.get(country)
        if not cc:
            log.warning("appbrain: unsupported country %s", country)
            return []

        url = f"{BASE_URL}/stats/google-play-rankings/top_free/game/{cc}"
        resp = self.session.get(url, timeout=self.timeout)
        resp.raise_for_status()
        return self._parse(resp.text, country)

    def _parse(self, html: str, country: str) -> list[SourceItem]:
        soup = BeautifulSoup(html, "html.parser")
        items: list[SourceItem] = []

        for row in soup.select("table.rankings-table tr, table tr"):
            cells = row.find_all("td")
            if len(cells) < 2:
                continue

            link = None
            for cell in cells:
                link = cell.find("a")
                if link:
                    break
            if not link:
                continue

            title = link.get_text(strip=True)
            if not title:
                continue

            href = link.get("href", "")
            app_url = href if href.startswith("http") else f"{BASE_URL}{href}"

            items.append(SourceItem(
                source=self.name,
                platform=self.platform,
                country=country,
                title=title,
                keyword=title,
                url=app_url,
                raw_score=float(len(items) + 1),
                tags=["app", "game", "android", "gaming"],
            ))
            if len(items) >= 20:
                break

        return items
