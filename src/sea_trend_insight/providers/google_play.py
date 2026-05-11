from __future__ import annotations

import logging
import re

from sea_trend_insight.models import SourceItem
from sea_trend_insight.providers.base import TrendProvider

log = logging.getLogger("sea_trend_insight")

COUNTRY_GL = {"PH": "PH", "ID": "ID", "TH": "TH"}
BASE_URL = "https://play.google.com"

GAME_PKG_HINTS = [
    "game", "legends", "fire", "craft", "clash", "roblox", "garena",
    "supercell", "gameloft", "tencent", "mihoyo", "pubg", "riot", "epic",
    "mahjong", "puzzle", "shooter", "racing", "rpg", "arcade", "casino",
    "chess", "king.", "zynga", "rovio", "candy", "temple", "subway",
    "block", "bubble", "word", "solitaire", "coloring", "cooking", "merge",
    "battle", "hero", "tower", "zombie", "dragon", "monster", "warrior",
    "quest", "saga", "adventure", "idle", "tycoon", "simulator", "strike",
    "sniper", "tank", "war", "army", "pixel", "ninja", "pirate",
    "com.dts.", "com.ea.", "com.rovio.", "com.miniclip.",
]


class GooglePlayProvider(TrendProvider):
    name = "google_play"
    platform = "android"

    def __init__(self, timeout: int = 40000, proxy: str | None = None):
        self.timeout = timeout
        self.proxy = proxy

    def fetch(self, country: str, date: str) -> list[SourceItem]:
        gl = COUNTRY_GL.get(country)
        if not gl:
            log.warning("google_play: unsupported country %s", country)
            return []

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            log.warning("google_play: playwright not installed, skipping")
            return []

        url = f"{BASE_URL}/store/apps/category/GAME?hl=en&gl={gl}"
        pw_proxy = {"server": self.proxy} if self.proxy else None

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, proxy=pw_proxy)
            try:
                page = browser.new_page()
                page.goto(url, wait_until="networkidle", timeout=self.timeout)
                for _ in range(3):
                    page.evaluate("window.scrollBy(0, 1000)")
                    page.wait_for_timeout(800)
                return self._extract(page, country)
            finally:
                browser.close()

    def _extract(self, page, country: str) -> list[SourceItem]:
        links = page.query_selector_all("a[href*='/store/apps/details']")
        seen: set[str] = set()
        items: list[SourceItem] = []

        for a in links:
            href = a.get_attribute("href") or ""
            m = re.search(r"id=([\w.]+)", href)
            if not m:
                continue
            pkg_id = m.group(1)
            if pkg_id in seen:
                continue
            seen.add(pkg_id)

            if not any(hint in pkg_id.lower() for hint in GAME_PKG_HINTS):
                continue

            title = a.inner_text().strip().split("\n")[0].strip()
            if not title or len(title) < 3:
                continue

            app_url = f"{BASE_URL}/store/apps/details?id={pkg_id}"
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
