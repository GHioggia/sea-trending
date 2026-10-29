from __future__ import annotations

import logging
import math
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import requests

from sea_trend_insight.models import SourceItem
from sea_trend_insight.providers.base import TrendProvider
from sea_trend_insight.providers.http_util import build_session, DEFAULT_TIMEOUT

log = logging.getLogger("sea_trend_insight")

COUNTRY_QUERY = {
    "PH": "sourcecountry:Philippines",
    "ID": "sourcecountry:Indonesia",
    "TH": "sourcecountry:Thailand",
}
COUNTRY_LANG = {"PH": "English", "ID": "Indonesian", "TH": "Thai"}
API_URL = "https://api.gdeltproject.org/api/v2/doc/doc"


class GdeltProvider(TrendProvider):
    name = "gdelt"
    platform = "gdelt"

    def __init__(self, timeout: int = DEFAULT_TIMEOUT, max_records: int = 30,
                 proxy: str | None = None, request_interval: float = 5.0,
                 max_retries: int = 2, backoff_factor: float = 5.0,
                 max_backoff: float = 60.0):
        for name, value in (("request_interval", request_interval),
                            ("backoff_factor", backoff_factor), ("max_backoff", max_backoff)):
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and non-negative")
        if not isinstance(max_retries, int) or max_retries < 0:
            raise ValueError("max_retries must be a non-negative integer")
        self.timeout = timeout
        self.max_records = max_records
        self.request_interval = request_interval
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.max_backoff = max_backoff
        # Own the retry budget here: adapter retries would bypass pacing.
        self.session = build_session(proxy=proxy, max_retries=0)
        self._next_request_at = 0.0

    def _retry_after(self, value: str | None) -> float | None:
        if value is None:
            return None
        try:
            if value.strip().isdigit():
                delay = float(value)
            else:
                deadline = parsedate_to_datetime(value)
                if deadline.tzinfo is None:
                    deadline = deadline.replace(tzinfo=timezone.utc)
                delay = (deadline - datetime.now(timezone.utc)).total_seconds()
            return max(0.0, delay) if math.isfinite(delay) else None
        except (ValueError, TypeError, OverflowError):
            return None

    def fetch(self, country: str, date: str) -> list[SourceItem]:
        query = COUNTRY_QUERY.get(country)
        if not query:
            log.warning("gdelt: unsupported country %s", country)
            return []

        params = {
            "query": query,
            "mode": "artlist",
            "format": "json",
            "maxrecords": str(self.max_records),
            "sort": "DateDesc",
        }
        backoff = min(self.backoff_factor, self.max_backoff)
        for attempt in range(self.max_retries + 1):
            wait = max(0.0, self._next_request_at - time.monotonic())
            if wait > max(self.max_backoff, self.request_interval):
                raise requests.HTTPError(
                    f"gdelt/{country}: HTTP 429 cooldown active ({wait:.1f}s remaining); "
                    "request skipped to respect Retry-After"
                )
            if wait:
                time.sleep(wait)
            # Shared across countries on this provider, including failed requests.
            self._next_request_at = time.monotonic() + self.request_interval
            resp = self.session.get(API_URL, params=params, timeout=self.timeout)
            if resp.status_code != 429:
                resp.raise_for_status()
                return self._parse(resp.json(), country)

            retry_after = self._retry_after(resp.headers.get("Retry-After"))
            delay = retry_after if retry_after is not None else backoff
            self._next_request_at = max(self._next_request_at, time.monotonic() + delay)
            log.warning("gdelt/%s: HTTP 429, attempt %d/%d, cooldown %.1fs",
                        country, attempt + 1, self.max_retries + 1, delay)
            resp.close()
            # Never shorten a server cooldown to fit the local wait budget.
            if attempt == self.max_retries or delay > self.max_backoff:
                resp.raise_for_status()
            backoff = min(backoff * 2, self.max_backoff)

    def _parse(self, data: dict, country: str) -> list[SourceItem]:
        articles = data.get("articles", [])
        items: list[SourceItem] = []
        for i, art in enumerate(articles):
            title = art.get("title", "")
            url = art.get("url", "")
            seen = art.get("seendate", "")
            domain = art.get("domain", "")
            lang = art.get("language", COUNTRY_LANG.get(country, ""))

            items.append(SourceItem(
                source=self.name,
                platform=self.platform,
                country=country,
                title=title,
                keyword=title[:80],
                url=url,
                published_at=seen,
                raw_score=float(len(articles) - i),
                language=lang.lower()[:2] if lang else None,
                tags=["news", domain] if domain else ["news"],
                summary=None,
            ))
        return items
