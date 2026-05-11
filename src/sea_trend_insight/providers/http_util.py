from __future__ import annotations

import logging
import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

log = logging.getLogger("sea_trend_insight")

DEFAULT_UA = "sea-trend-insight/0.1 (+https://github.com/user/sea-trending)"
DEFAULT_TIMEOUT = 20
DEFAULT_RETRIES = 2


def _proxy_dict(proxy_url: str | None = None) -> dict[str, str] | None:
    url = proxy_url or os.environ.get("SEA_TREND_PROXY", "")
    if not url:
        return None
    return {"http": url, "https": url}


def build_session(
    user_agent: str = DEFAULT_UA,
    max_retries: int = DEFAULT_RETRIES,
    proxy: str | None = None,
) -> requests.Session:
    session = requests.Session()
    session.headers["User-Agent"] = user_agent
    proxies = _proxy_dict(proxy)
    if proxies:
        session.proxies.update(proxies)
        log.debug("Using proxy: %s", proxy or os.environ.get("SEA_TREND_PROXY"))
    retry = Retry(
        total=max_retries,
        backoff_factor=0.6,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def get(url: str, session: requests.Session | None = None,
        timeout: int = DEFAULT_TIMEOUT, **kwargs) -> requests.Response:
    s = session or build_session()
    log.debug("GET %s", url)
    resp = s.get(url, timeout=timeout, **kwargs)
    resp.raise_for_status()
    return resp
