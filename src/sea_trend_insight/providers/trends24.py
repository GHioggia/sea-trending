from __future__ import annotations

import logging
from urllib.parse import quote_plus

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
BASE_URL = "https://trends24.in"


def _x_url(text: str) -> str:
    tag = text.lstrip("#")
    if text.startswith("#"):
        return f"https://x.com/hashtag/{quote_plus(tag)}"
    return f"https://x.com/search?q={quote_plus(text)}"


class Trends24Provider(TrendProvider):
    name = "trends24"
    platform = "twitter"

    def __init__(self, timeout: int = DEFAULT_TIMEOUT, proxy: str | None = None):
        self.timeout = timeout
        self.session = build_session(proxy=proxy)

    def fetch(self, country: str, date: str) -> list[SourceItem]:
        slug = COUNTRY_SLUG.get(country)
        if not slug:
            log.warning("trends24: unsupported country %s", country)
            return []

        url = f"{BASE_URL}/{slug}/"
        resp = self.session.get(url, timeout=self.timeout)
        resp.raise_for_status()
        return self._parse(resp.text, country)

    def _parse(self, html: str, country: str) -> list[SourceItem]:
        soup = BeautifulSoup(html, "html.parser")
        items: list[SourceItem] = []
        seen: set[str] = set()

        for tag in soup.select("li a[href*='/trend/']"):
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
                url=_x_url(text),
                raw_score=float(len(items) + 1),
                tags=["twitter", "trending"],
            ))
            if len(items) >= 30:
                break

        if not items:
            for tag in soup.select("ol li a, .trend-card li a, .list-group-item"):
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
                    url=_x_url(text),
                    raw_score=float(len(items) + 1),
                    tags=["twitter", "trending"],
                ))
                if len(items) >= 30:
                    break

        return items
