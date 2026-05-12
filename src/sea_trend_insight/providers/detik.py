from __future__ import annotations

import logging
import re

import feedparser
from bs4 import BeautifulSoup

from sea_trend_insight.models import SourceItem
from sea_trend_insight.providers.base import TrendProvider
from sea_trend_insight.providers.http_util import build_session, DEFAULT_TIMEOUT

log = logging.getLogger("sea_trend_insight")

TERPOPULER_URL = "https://www.detik.com/terpopuler"
FALLBACK_RSS = "https://hot.detik.com/rss"


class DetikProvider(TrendProvider):
    name = "detik"
    platform = "web"

    def __init__(self, timeout: int = DEFAULT_TIMEOUT, proxy: str | None = None):
        self.timeout = timeout
        self.session = build_session(proxy=proxy)

    def fetch(self, country: str, date: str) -> list[SourceItem]:
        if country != "ID":
            return []

        try:
            resp = self.session.get(TERPOPULER_URL, timeout=self.timeout)
            resp.raise_for_status()
            items = self._parse_terpopuler(resp.text, country)
            if items:
                return items
        except Exception as exc:
            log.warning("detik: terpopuler failed: %s", exc)

        return self._fetch_rss(country)

    def _parse_terpopuler(self, html: str, country: str) -> list[SourceItem]:
        soup = BeautifulSoup(html, "html.parser")
        items: list[SourceItem] = []

        for article in soup.select("article.list-content__item"):
            title_tag = article.select_one(".media__title a, h3 a, h2 a")
            link_tag = article.select_one("a.media__link") or article.select_one("a[href]")
            if not title_tag or not link_tag:
                continue
            title = title_tag.get_text(strip=True)
            url = link_tag.get("href", "")
            if not title or not url:
                continue

            items.append(SourceItem(
                source=self.name,
                platform=self.platform,
                country=country,
                title=title,
                keyword=title[:80],
                url=url,
                raw_score=float(20 - len(items)),
                language="id",
                tags=["news", "indonesia", "terpopuler"],
            ))
            if len(items) >= 20:
                break

        return items

    def _fetch_rss(self, country: str) -> list[SourceItem]:
        try:
            resp = self.session.get(FALLBACK_RSS, timeout=self.timeout)
            resp.raise_for_status()
            return self._parse_rss(resp.text, country)
        except Exception as exc:
            log.warning("detik: RSS fallback also failed: %s", exc)
            return []

    def _parse_rss(self, xml_text: str, country: str) -> list[SourceItem]:
        feed = feedparser.parse(xml_text)
        items: list[SourceItem] = []
        for i, entry in enumerate(feed.entries[:20]):
            title = entry.get("title", "")
            link = entry.get("link", "")
            if not title:
                continue
            items.append(SourceItem(
                source=self.name,
                platform=self.platform,
                country=country,
                title=title,
                keyword=title[:80],
                url=link,
                published_at=entry.get("published", ""),
                raw_score=float(20 - i),
                language="id",
                tags=["news", "indonesia"],
                summary=re.sub(r"<[^>]+>", " ", entry.get("summary", "")).strip()[:200] or None,
            ))
        return items
