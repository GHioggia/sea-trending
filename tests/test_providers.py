"""Tests for all live providers using local fixtures (no network)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


# ── Google News ──────────────────────────────────────────────

def test_google_news_parse():
    from sea_trend_insight.providers.google_news import GoogleNewsProvider

    provider = GoogleNewsProvider()
    xml = (FIXTURES / "google_news_PH.xml").read_text()
    items = provider._parse(xml, "PH")

    assert len(items) == 5
    assert all(it.country == "PH" for it in items)
    assert all(it.source == "google_news" for it in items)
    assert any("PhilHealth" in it.title for it in items)
    assert any("Mobile Legends" in it.title for it in items)
    assert any("Typhoon" in it.title for it in items)
    # title should strip " - Source" suffix
    for it in items:
        assert " - " not in it.title


# ── GDELT ────────────────────────────────────────────────────

def test_gdelt_parse():
    from sea_trend_insight.providers.gdelt import GdeltProvider

    provider = GdeltProvider()
    data = json.loads((FIXTURES / "gdelt_PH.json").read_text())
    items = provider._parse(data, "PH")

    assert len(items) == 4
    assert all(it.source == "gdelt" for it in items)
    assert all(it.country == "PH" for it in items)
    assert any("Typhoon" in it.title for it in items)
    assert any("Mobile Legends" in it.title for it in items)
    assert items[0].raw_score > items[-1].raw_score


# ── Trends24 ─────────────────────────────────────────────────

def test_trends24_parse():
    from sea_trend_insight.providers.trends24 import Trends24Provider

    provider = Trends24Provider()
    html = (FIXTURES / "trends24_PH.html").read_text()
    items = provider._parse(html, "PH")

    assert len(items) >= 5
    assert all(it.source == "trends24" for it in items)
    keywords = {it.keyword for it in items}
    assert "MobileLegendsUpdate" in keywords or any("MobileLegends" in k for k in keywords)
    assert any("Typhoon" in it.keyword for it in items)


# ── GetDayTrends ─────────────────────────────────────────────

def test_getdaytrends_parse():
    from sea_trend_insight.providers.getdaytrends import GetDayTrendsProvider

    provider = GetDayTrendsProvider()
    html = (FIXTURES / "getdaytrends_PH.html").read_text()
    items = provider._parse(html, "PH")

    assert len(items) == 6
    assert all(it.source == "getdaytrends" for it in items)
    assert items[0].keyword == "MPL PH Season 14"
    assert items[0].raw_score == 200_000.0
    assert items[1].raw_score == 500_000.0


def test_getdaytrends_volume_parser():
    from sea_trend_insight.providers.getdaytrends import GetDayTrendsProvider

    p = GetDayTrendsProvider._parse_volume
    assert p("200K+") == 200_000.0
    assert p("1.5M") == 1_500_000.0
    assert p("50000") == 50_000.0
    assert p("") == 0.0
    assert p("N/A") == 0.0


# ── Kworb YouTube ────────────────────────────────────────────

def test_kworb_youtube_parse():
    from sea_trend_insight.providers.kworb_youtube import KworbYouTubeProvider

    provider = KworbYouTubeProvider()
    html = (FIXTURES / "kworb_youtube_PH.html").read_text()
    items = provider._parse(html, "PH")

    assert len(items) == 5
    assert all(it.source == "kworb_youtube" for it in items)
    assert all(it.platform == "youtube" for it in items)
    assert any("Mobile Legends" in it.title for it in items)
    assert items[0].raw_score == 15_230_000.0


# ── AppBrain ─────────────────────────────────────────────────

def test_appbrain_parse():
    from sea_trend_insight.providers.appbrain import AppBrainProvider

    provider = AppBrainProvider()
    html = (FIXTURES / "appbrain_PH.html").read_text()
    items = provider._parse(html, "PH")

    assert len(items) == 5
    assert all(it.source == "appbrain" for it in items)
    assert all(it.platform == "android" for it in items)
    assert items[0].keyword == "Mobile Legends: Bang Bang"
    assert "gaming" in items[0].tags


# ── Appfigures ───────────────────────────────────────────────

def test_appfigures_parse():
    from sea_trend_insight.providers.appfigures import AppfiguresProvider

    provider = AppfiguresProvider(api_key="test")
    data = json.loads((FIXTURES / "appfigures_PH.json").read_text())
    items = provider._parse(data, "PH")

    assert len(items) == 3
    assert items[0].keyword == "Mobile Legends: Bang Bang"
    assert items[0].summary == "Moonton"


def test_appfigures_no_key():
    from sea_trend_insight.providers.appfigures import AppfiguresProvider

    provider = AppfiguresProvider()
    items = provider.fetch("PH", "2026-05-09")
    assert items == []


# ── Classifier with new keywords ─────────────────────────────

def test_classifier_new_keywords():
    from sea_trend_insight.classifier import classify
    from sea_trend_insight.models import NormalizedItem

    def _item(keyword, title=""):
        return NormalizedItem(
            keyword=keyword, country="PH", source="t", platform="t",
            category="", title=title or keyword,
        )

    assert classify(_item("เกมมือถือ ยอดนิยม")) == "gaming"
    assert classify(_item("mabar MLBB bareng")) == "gaming"
    assert classify(_item("gim terbaru Indonesia")) == "gaming"
    assert classify(_item("banjir Jakarta Selatan")) == "news"
    assert classify(_item("harga BBM naik lagi")) == "news"
    assert classify(_item("ค่าไฟ ขึ้นราคา")) == "news"
    assert classify(_item("power outage Luzon")) == "news"
    assert classify(_item("hantu viral video horor")) == "viral"
    assert classify(_item("ดราม่า ล่าสุด trending")) == "viral"
    assert classify(_item("ghost haunted house trending")) == "viral"
    assert classify(_item("SB19 concert dates")) == "trending"
