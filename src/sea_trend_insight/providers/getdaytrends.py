from __future__ import annotations

import logging

from bs4 import BeautifulSoup

from sea_trend_insight.models import SourceItem
from sea_trend_insight.providers.base import TrendProvider
from sea_trend_insight.providers.http_util import build_session, DEFAULT_TIMEOUT

log = logging.getLogger("sea_trend_insight")

COUNTRY_SLUG = {
    "PH": "philippines",
    "ID": "indonesia",
    "TH": "thailand",
}
BASE_URL = "https://getdaytrends.com"


class GetDayTrendsProvider(TrendProvider):
    name = "getdaytrends"
    platform = "twitter"

    def __init__(self, timeout: int = DEFAULT_TIMEOUT, proxy: str | None = None):
        self.timeout = timeout
        self.session = build_session(proxy=proxy)

    def fetch(self, country: str, date: str) -> list[SourceItem]:
        slug = COUNTRY_SLUG.get(country)
        if not slug:
            log.warning("getdaytrends: unsupported country %s", country)
            return []

        url = f"{BASE_URL}/{slug}/"
        resp = self.session.get(url, timeout=self.timeout)
        resp.raise_for_status()
        return self._parse(resp.text, country)

    def _parse(self, html: str, country: str) -> list[SourceItem]:
        soup = BeautifulSoup(html, "html.parser")
        items: list[SourceItem] = []
        seen: set[str] = set()

        for row in soup.select("table tr"):
            cells = row.find_all("td")
            if not cells:
                continue
            link = cells[0].find("a")
            if link:
                text = link.get_text(strip=True)
            else:
                text = cells[0].get_text(strip=True)
            if not text or text.lower() in seen:
                continue
            seen.add(text.lower())

            volume = cells[1].get_text(strip=True) if len(cells) > 1 else ""

            items.append(SourceItem(
                source=self.name,
                platform=self.platform,
                country=country,
                title=text,
                keyword=text.lstrip("#"),
                url=f"{BASE_URL}/{COUNTRY_SLUG[country]}/",
                raw_score=self._parse_volume(volume),
                tags=["twitter", "trending"],
                summary=f"Volume: {volume}" if volume else None,
            ))
            if len(items) >= 30:
                break

        if not items:
            for tag in soup.select("a.list-group-item, .trend-name a, ol li a"):
                text = tag.get_text(strip=True)
                if not text or text.lower() in seen:
                    continue
                seen.add(text.lower())
                items.append(SourceItem(
                    source=self.name,
                    platform=self.platform,
                    country=country,
                    title=text,
                    keyword=text.lstrip("#"),
                    raw_score=float(len(items) + 1),
                    tags=["twitter", "trending"],
                ))
                if len(items) >= 30:
                    break

        return items

    @staticmethod
    def _parse_volume(v: str) -> float:
        v = v.strip().upper().replace(",", "").replace("+", "")
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
