from __future__ import annotations

import json
import logging
import re

from sea_trend_insight.models import SourceItem
from sea_trend_insight.providers.base import TrendProvider
from sea_trend_insight.providers.http_util import build_session, DEFAULT_TIMEOUT

log = logging.getLogger("sea_trend_insight")

BASE_URL = "https://today.line.me"
PAGE_URL = f"{BASE_URL}/th"
ARTICLE_URL = f"{BASE_URL}/th/v2/article"


class LineTodayProvider(TrendProvider):
    name = "line_today"
    platform = "web"

    def __init__(self, timeout: int = DEFAULT_TIMEOUT, proxy: str | None = None):
        self.timeout = timeout
        self.session = build_session(proxy=proxy)

    def fetch(self, country: str, date: str) -> list[SourceItem]:
        if country != "TH":
            return []

        try:
            resp = self.session.get(PAGE_URL, timeout=self.timeout)
            resp.raise_for_status()
            return self._parse(resp.text, country)
        except Exception as exc:
            log.warning("line_today: fetch failed: %s", exc)
            return []

    def _parse(self, html: str, country: str) -> list[SourceItem]:
        m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
        if not m:
            log.warning("line_today: __NEXT_DATA__ not found")
            return []

        try:
            data = json.loads(m.group(1))
        except json.JSONDecodeError as exc:
            log.warning("line_today: JSON parse error: %s", exc)
            return []

        modules = self._dig(data, "props", "pageProps", "fallback", "getPageData,top", "modules") or []
        items: list[SourceItem] = []

        for module in modules:
            module_items = module.get("items") or module.get("data", {}).get("items", [])
            for entry in module_items:
                item = self._extract_item(entry, country, len(items))
                if item:
                    items.append(item)
                    if len(items) >= 25:
                        return items

        if not items:
            log.info("line_today: no items from modules, trying flat article scan")
            items = self._scan_articles(data, country)

        return items

    def _extract_item(self, entry: dict, country: str, rank: int) -> SourceItem | None:
        title = (
            entry.get("title")
            or entry.get("name")
            or (entry.get("link") or {}).get("tag")
        )
        if not title:
            return None

        content_id = entry.get("contentId") or entry.get("id") or ""
        link_data = entry.get("link") or {}
        url = (
            link_data.get("url")
            or (f"{ARTICLE_URL}/{content_id}" if content_id else None)
            or f"{BASE_URL}/th/v2/tab/trending"
        )

        return SourceItem(
            source=self.name,
            platform=self.platform,
            country=country,
            title=title,
            keyword=title[:80],
            url=url,
            raw_score=float(25 - rank),
            language="th",
            tags=["news", "thailand"],
            summary=entry.get("summary") or entry.get("description") or None,
        )

    def _scan_articles(self, data: dict, country: str) -> list[SourceItem]:
        """Fallback: recursively find article-like dicts anywhere in the NEXT_DATA."""
        items: list[SourceItem] = []
        self._recurse(data, items, country, depth=0)
        return items[:25]

    def _recurse(self, node, items: list, country: str, depth: int) -> None:
        if depth > 8 or len(items) >= 25:
            return
        if isinstance(node, dict):
            title = node.get("title") or node.get("name") or ""
            content_id = node.get("contentId") or node.get("id") or ""
            if title and isinstance(title, str) and len(title) > 10 and content_id:
                url = node.get("url") or (f"{ARTICLE_URL}/{content_id}" if content_id else None)
                items.append(SourceItem(
                    source=self.name,
                    platform=self.platform,
                    country=country,
                    title=title,
                    keyword=title[:80],
                    url=url,
                    raw_score=float(25 - len(items)),
                    language="th",
                    tags=["news", "thailand"],
                ))
                return
            for v in node.values():
                self._recurse(v, items, country, depth + 1)
        elif isinstance(node, list):
            for v in node:
                self._recurse(v, items, country, depth + 1)

    @staticmethod
    def _dig(obj, *keys):
        for k in keys:
            if not isinstance(obj, dict):
                return None
            obj = obj.get(k)
        return obj
