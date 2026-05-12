"""TikTok trending provider via Apify (unseenuser/tiktok-trend-hunter)."""
from __future__ import annotations

import logging
import os

from sea_trend_insight.models import SourceItem
from sea_trend_insight.providers.base import TrendProvider
from sea_trend_insight.providers.http_util import build_session

log = logging.getLogger("sea_trend_insight")

COUNTRY_REGION = {"PH": "PH", "ID": "ID", "TH": "TH"}

APIFY_RUN_TIMEOUT = 120   # seconds allowed for the Apify actor run
REQUESTS_TIMEOUT = 150    # slightly longer to absorb Apify's own timeout


class TiktokProvider(TrendProvider):
    name = "tiktok"
    platform = "tiktok"

    def __init__(
        self,
        apify_token: str | None = None,
        actor_id: str = "unseenuser~tiktok-trend-hunter",
        max_results: int = 30,
        proxy: str | None = None,
    ):
        self.apify_token = apify_token
        self.actor_id = actor_id
        self.max_results = max_results
        self.session = build_session(proxy=proxy)

    def fetch(self, country: str, date: str) -> list[SourceItem]:
        if not self.apify_token:
            log.warning("tiktok: no Apify token configured (env: APIFY_API_KEY), skipping")
            return []

        region = COUNTRY_REGION.get(country)
        if not region:
            log.warning("tiktok: unsupported country %s", country)
            return []

        url = (
            f"https://api.apify.com/v2/acts/{self.actor_id}"
            "/run-sync-get-dataset-items"
        )
        try:
            resp = self.session.post(
                url,
                params={"token": self.apify_token, "timeout": APIFY_RUN_TIMEOUT},
                json={
                    "mode": "trending_feed",
                    "region": region,
                    "maxResults": self.max_results,
                },
                timeout=REQUESTS_TIMEOUT,
            )
            resp.raise_for_status()
            return self._parse(resp.json(), country)
        except Exception as e:
            log.error("tiktok/%s: Apify request failed: %s", country, e)
            return []

    def _parse(self, data: list[dict], country: str) -> list[SourceItem]:
        items: list[SourceItem] = []
        for row in data:
            if row.get("rowType") != "video":
                continue

            caption = (row.get("caption") or "").strip()
            hashtags: list[str] = row.get("hashtags") or []
            keyword = hashtags[0] if hashtags else (caption[:80] or "tiktok_trend")

            view_count = int(row.get("viewCount") or 0)
            like_count = int(row.get("likeCount") or 0)
            share_count = int(row.get("shareCount") or 0)
            virality = row.get("viralityScore") or 0.0

            summary = (
                f"views={view_count:,} likes={like_count:,} "
                f"shares={share_count:,} virality={virality:.1f}"
            )

            tags = hashtags[:5] + ["tiktok", "viral"]

            items.append(SourceItem(
                source=self.name,
                platform=self.platform,
                country=country,
                title=caption[:120] if caption else keyword,
                keyword=keyword,
                url=row.get("url") or "",
                published_at=row.get("postedAt") or "",
                raw_score=float(view_count),
                tags=tags,
                summary=summary,
            ))

        return items
