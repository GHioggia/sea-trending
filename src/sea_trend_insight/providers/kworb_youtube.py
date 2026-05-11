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

        for row in table.find_all("tr"):
            cells = row.find_all("td")
            # real kworb layout: rank | change | title(link)
            # find the cell that contains a link to YouTube
            link = None
            for cell in cells:
                a = cell.find("a", href=True)
                if a and ("youtu" in a.get("href", "") or "youtube" in a.get("href", "")):
                    link = a
                    break
            if not link:
                continue

            title = link.get_text(strip=True)
            if not title:
                continue

            href = link["href"]
            # href is already a full YouTube URL: https://youtu.be/ID or https://www.youtube.com/watch?v=ID
            if href.startswith("https://youtu.be/"):
                vid_id = href.split("/")[-1]
                vid_url = f"https://www.youtube.com/watch?v={vid_id}"
            else:
                vid_url = href

            items.append(SourceItem(
                source=self.name,
                platform=self.platform,
                country=country,
                title=title,
                keyword=title[:80],
                url=vid_url,
                raw_score=float(len(items) + 1),
                tags=["youtube", "video"],
            ))
            if len(items) >= 25:
                break

        return items
