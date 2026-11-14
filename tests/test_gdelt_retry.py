"""Offline rate-limit regressions; fake time and responses, no GDELT calls."""
import json
from dataclasses import replace
from datetime import datetime, timezone
from email.utils import format_datetime
from unittest.mock import Mock

import pytest
import requests
from urllib3 import HTTPConnectionPool, HTTPResponse

from sea_trend_insight.providers import gdelt
from sea_trend_insight.providers.http_util import build_session


class Clock:
    now = 0.0

    def __init__(self):
        self.waits = []

    def sleep(self, seconds):
        self.waits.append(seconds)
        self.now += seconds


@pytest.fixture
def clock(monkeypatch):
    clock = Clock()
    monkeypatch.setattr(gdelt.time, "monotonic", lambda: clock.now)
    monkeypatch.setattr(gdelt.time, "sleep", clock.sleep)
    return clock


def response(status=200, retry_after=None):
    resp = requests.Response()
    resp.status_code = status
    resp.url = gdelt.API_URL
    resp._content = b'{"articles": [{"title": "News", "url": "https://example.org/news"}]}'
    resp._content_consumed = True
    if retry_after is not None:
        resp.headers["Retry-After"] = retry_after
    return resp


def provider_with(*responses, **kwargs):
    provider = gdelt.GdeltProvider(**kwargs)
    provider.session.get = Mock(side_effect=responses)
    return provider


def test_cross_country_spacing(clock):
    provider = provider_with(response(), response(), response(), request_interval=7)
    for country in ("PH", "ID", "TH"):
        assert provider.fetch(country, "2026-10-29")[0].country == country
    assert clock.waits == [7, 7]


@pytest.mark.parametrize("header,expected", [("12", 12), ("0", 5), (None, 8),
                                              ("invalid", 8), ("-1", 8)])
def test_429_recovers(clock, header, expected):
    provider = provider_with(response(429, header), response(), backoff_factor=8)
    assert len(provider.fetch("PH", "2026-10-29")) == 1
    assert provider.session.get.call_count == 2
    assert clock.waits == [expected]


def test_retry_after_http_date(clock, monkeypatch):
    now = datetime(2026, 10, 29, tzinfo=timezone.utc)
    fake_datetime = Mock()
    fake_datetime.now.return_value = now
    monkeypatch.setattr(gdelt, "datetime", fake_datetime)
    header = format_datetime(datetime(2026, 10, 29, 0, 0, 15, tzinfo=timezone.utc), usegmt=True)
    provider = provider_with(response(429, header), response())
    provider.fetch("ID", "2026-10-29")
    assert clock.waits == [15]


def test_persistent_429_has_bounded_backoff_and_attempts(clock):
    provider = provider_with(*(response(429) for _ in range(4)),
                             max_retries=3, backoff_factor=10, max_backoff=15)
    with pytest.raises(requests.HTTPError, match="429"):
        provider.fetch("ID", "2026-10-29")
    assert provider.session.get.call_count == 4
    assert clock.waits == [10, 15, 15]  # No sleep after final failure.
    assert provider._next_request_at == clock.now + 15


def test_long_retry_after_preserves_cooldown_without_early_requests(clock):
    provider = provider_with(response(429, "120"), response(), max_backoff=30)
    with pytest.raises(requests.HTTPError, match="429"):
        provider.fetch("PH", "2026-10-29")
    with pytest.raises(requests.HTTPError, match="cooldown active"):
        provider.fetch("ID", "2026-10-29")
    assert provider.session.get.call_count == 1
    assert clock.waits == []
    clock.now = 120
    assert provider.fetch("TH", "2026-10-29")


def test_final_429_cooldown_applies_to_next_country(clock):
    provider = provider_with(response(429, "20"), response(), max_retries=0)
    with pytest.raises(requests.HTTPError):
        provider.fetch("PH", "2026-10-29")
    assert provider.fetch("ID", "2026-10-29")
    assert clock.waits == [20]


def test_other_http_errors_are_not_retried(clock):
    provider = provider_with(response(403))
    with pytest.raises(requests.HTTPError, match="403"):
        provider.fetch("TH", "2026-10-29")
    assert provider.session.get.call_count == 1
    assert not clock.waits


def test_adapter_does_not_hide_or_retry_429(monkeypatch):
    retry = gdelt.GdeltProvider().session.get_adapter(gdelt.API_URL).max_retries
    pool = HTTPConnectionPool("offline.invalid")
    make_request = Mock(return_value=HTTPResponse(status=429, headers={"Retry-After": "120"}))
    monkeypatch.setattr(pool, "_make_request", make_request)
    assert pool.urlopen("GET", "/", retries=retry).status == 429
    assert make_request.call_count == 1
    assert build_session().get_adapter(gdelt.API_URL).max_retries.total == 2


@pytest.mark.parametrize("kwargs", [{"request_interval": -1}, {"max_retries": -1},
                                    {"max_retries": 1.5}, {"backoff_factor": float("nan")},
                                    {"max_backoff": float("inf")}])
def test_invalid_config(kwargs):
    with pytest.raises(ValueError):
        gdelt.GdeltProvider(**kwargs)


def test_config_wiring():
    from sea_trend_insight.runner import _build_live_providers
    providers = _build_live_providers({"providers": {"gdelt": {
        "enabled": True, "request_interval": 9, "max_retries": 1,
        "backoff_factor": 12, "max_backoff": 24,
    }}})
    provider, = providers
    assert (provider.request_interval, provider.max_retries,
            provider.backoff_factor, provider.max_backoff) == (9, 1, 12, 24)


@pytest.mark.parametrize("fail_all", [False, True])
def test_partial_failure_still_writes_report_and_country_status(clock, monkeypatch, tmp_path, fail_all):
    from sea_trend_insight import runner
    from sea_trend_insight.config import load_config
    from sea_trend_insight.providers.base import TrendProvider

    cfg = load_config()
    cfg["llm"]["enabled"] = False
    replies = ([response(429)] * 3 if fail_all else
               [response(), response(429), response()])
    provider = provider_with(*replies, max_retries=0)

    class OtherProvider(TrendProvider):
        name = "other"
        platform = "web"

        def fetch(self, country, date):
            items = provider._parse({"articles": [{"title": "Other news " + country,
                                                   "url": "https://other.org/" + country}]}, country)
            return [replace(item, source=self.name, platform=self.platform) for item in items]

    monkeypatch.setattr(runner, "load_config", lambda _: cfg)
    monkeypatch.setattr(runner, "project_root", lambda: tmp_path)
    monkeypatch.setattr(runner, "_build_live_providers", lambda _: [provider, OtherProvider()])
    result = runner.cmd_run("2026-10-29", ["PH", "ID", "TH"], live=True)
    expected = {"gdelt_PH": "failed" if fail_all else "ok", "gdelt_ID": "failed",
                "gdelt_TH": "failed" if fail_all else "ok",
                "other_PH": "ok", "other_ID": "ok", "other_TH": "ok"}
    assert result["providers_status"] == expected
    assert len(result["errors"]) == (3 if fail_all else 1)
    assert all("429" in error for error in result["errors"])
    saved = json.loads((tmp_path / "logs/2026-10-29-run.json").read_text())
    assert saved["providers_status"] == expected
    assert (tmp_path / "reports/2026-10-29/report.json").exists()
    html = (tmp_path / "public/2026-10-29.html").read_text()
    assert "gdelt/ID" in html and "429" in html
