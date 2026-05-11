from __future__ import annotations

import logging

from bs4 import BeautifulSoup

from sea_trend_insight.models import SourceItem
from sea_trend_insight.providers.base import TrendProvider
from sea_trend_insight.providers.http_util import build_session, DEFAULT_TIMEOUT

log = logging.getLogger("sea_trend_insight")

COUNTRY_CODE = {"PH": "ph", "ID": "id", "TH": "th"}
BASE_URL = "https://kworb.net"


class KworbYouTubeProvider(TrendProvider):
    name = "kworb_youtube"
    platform = "youtube"

    def __init__(self, timeout: int = DEFAULT_TIMEOUT, proxy: str | None = None):
        self.timeout = timeout
        self.session = build_session(proxy=proxy)

    def fetch(self, country: str, date: str) -> list[SourceItem]:
        cc = COUNTRY_CODE.get(country)
        if not cc:
            log.warning("kworb_youtube: unsupported country %s", country)
            return []

        url = f"{BASE_URL}/youtube/trending/{cc}.html"
        resp = self.session.get(url, timeout=self.timeout)
        resp.raise_for_status()
        return self._parse(resp.text, country)

    def _parse(self, html: str, country: str) -> list[SourceItem]:
        soup = BeautifulSoup(html, "html.parser")
        items: list[SourceItem] = []

        table = soup.find("table")
        if not table:
            log.warning("kworb_youtube: no table found in page")
            return []

        for row in table.find_all("tr")[1:]:
            cells = row.find_all("td")
            if len(cells) < 2:
                continue
            link = cells[0].find("a")
            if link:
                title = link.get_text(strip=True)
                href = link.get("href", "")
                vid_url = href if href.startswith("http") else f"{BASE_URL}{href}"
            else:
                title = cells[0].get_text(strip=True)
                vid_url = None

            if not title:
                continue

            views_text = cells[1].get_text(strip=True) if len(cells) > 1 else ""

            items.append(SourceItem(
                source=self.name,
                platform=self.platform,
                country=country,
                title=title,
                keyword=title[:80],
                url=vid_url,
                raw_score=self._parse_views(views_text),
                tags=["youtube", "video"],
                summary=f"Views: {views_text}" if views_text else None,
            ))
            if len(items) >= 25:
                break

        return items

    @staticmethod
    def _parse_views(v: str) -> float:
        v = v.strip().replace(",", "").replace("+", "")
        try:
            return float(v)
        except ValueError:
            return 0.0
