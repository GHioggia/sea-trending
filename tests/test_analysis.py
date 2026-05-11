"""Tests for dedup, scoring, analyzer modules."""
from __future__ import annotations

from sea_trend_insight.models import NormalizedItem, ScoredItem, ScoreBreakdown


def _item(keyword="test", country="PH", source="google_trends", platform="google",
          title="", url=None, score=0.0, tags=None, summary=None, category="trending"):
    return NormalizedItem(
        keyword=keyword, country=country, source=source, platform=platform,
        category=category, title=title or keyword, url=url, score=score,
        tags=tags or [], summary=summary,
    )


# ── Dedup ──────────────────────────────────────────────────────

class TestDedup:
    def test_url_dedup(self):
        from sea_trend_insight.dedup import deduplicate

        items = [
            _item("A", url="https://example.com/1", score=10),
            _item("B", url="https://example.com/1", score=20),
        ]
        result, log = deduplicate(items)
        assert len(result) == 1
        assert result[0].score == 20
        assert len(log) == 1

    def test_url_dedup_ignores_query(self):
        from sea_trend_insight.dedup import deduplicate

        items = [
            _item("A", url="https://example.com/1?ref=a", score=10),
            _item("B", url="https://example.com/1?ref=b", score=20),
        ]
        result, _ = deduplicate(items)
        assert len(result) == 1

    def test_keyword_dedup(self):
        from sea_trend_insight.dedup import deduplicate

        items = [
            _item("Mobile Legends", score=10),
            _item("mobile legends", score=20),
        ]
        result, log = deduplicate(items)
        assert len(result) == 1
        assert result[0].score == 20

    def test_title_similarity_dedup(self):
        from sea_trend_insight.dedup import deduplicate

        items = [
            _item("A", title="Typhoon Carina hits Manila area", score=10),
            _item("B", title="Typhoon Carina hits Manila region", score=20),
        ]
        result, _ = deduplicate(items)
        assert len(result) == 1

    def test_no_dedup_different_country(self):
        from sea_trend_insight.dedup import deduplicate

        items = [
            _item("Mobile Legends", country="PH", score=10),
            _item("Mobile Legends", country="ID", score=20),
        ]
        result, _ = deduplicate(items)
        assert len(result) == 2

    def test_no_dedup_different_content(self):
        from sea_trend_insight.dedup import deduplicate

        items = [
            _item("Typhoon", title="Typhoon hits Manila"),
            _item("Election", title="Election results announced"),
        ]
        result, _ = deduplicate(items)
        assert len(result) == 2

    def test_empty_input(self):
        from sea_trend_insight.dedup import deduplicate

        result, log = deduplicate([])
        assert result == []
        assert log == []


# ── Classifier ─────────────────────────────────────────────────

class TestClassifierImproved:
    def test_google_play_always_gaming(self):
        from sea_trend_insight.classifier import classify

        item = _item("Nikkei Index App", source="google_play", platform="android")
        assert classify(item) == "gaming"

    def test_nikkei_not_gaming_from_news(self):
        from sea_trend_insight.classifier import classify

        item = _item("Nikkei index drops", source="google_news", platform="google",
                      title="Nikkei stock market drops 3%")
        assert classify(item) == "news"

    def test_strong_gaming_keyword_from_news(self):
        from sea_trend_insight.classifier import classify

        item = _item("Genshin Impact update", source="google_news", title="Genshin Impact 5.0")
        assert classify(item) == "gaming"

    def test_gdelt_defaults_to_news(self):
        from sea_trend_insight.classifier import classify

        item = _item("some random topic", source="gdelt", platform="gdelt")
        assert classify(item) == "news"

    def test_game_word_without_news_context(self):
        from sea_trend_insight.classifier import classify

        item = _item("New game released", source="trends24", platform="twitter",
                      title="Exciting new game launch")
        assert classify(item) == "gaming"

    def test_classify_with_debug(self):
        from sea_trend_insight.classifier import classify_with_debug

        item = _item("MPL PH Season 14", source="trends24")
        cat, debug = classify_with_debug(item)
        assert cat == "gaming"
        assert "reason" in debug


# ── Scorer ─────────────────────────────────────────────────────

class TestScorer:
    def test_score_items(self):
        from sea_trend_insight.scorer import score_items

        items = [
            _item("Mobile Legends", score=200000, category="gaming"),
            _item("Typhoon Carina", score=150000, category="news"),
        ]
        scored = score_items(items)
        assert len(scored) == 2
        assert scored[0].scores.game_design_value > 0
        assert scored[0].scores.relevance > 0

    def test_gaming_item_high_gdv(self):
        from sea_trend_insight.scorer import score_items

        items = [_item("Genshin Impact 5.0", score=100000, category="gaming",
                        tags=["gaming", "genshin impact"])]
        scored = score_items(items)
        assert scored[0].scores.game_design_value >= 0.6

    def test_risk_score_sensitive(self):
        from sea_trend_insight.scorer import score_items

        items = [_item("Drug cartel busted", score=50000, category="news",
                        title="Drug cartel operation")]
        scored = score_items(items)
        assert scored[0].scores.risk >= 0.5

    def test_virality_score_viral_keyword(self):
        from sea_trend_insight.scorer import score_items

        items = [_item("Dance challenge viral", score=200000, category="viral",
                        title="TikTok dance challenge goes viral")]
        scored = score_items(items)
        assert scored[0].scores.virality > 0.3

    def test_debug_fields_present(self):
        from sea_trend_insight.scorer import score_items

        items = [_item("Test item", score=100000)]
        scored = score_items(items)
        debug = scored[0].scores.debug
        assert "relevance" in debug
        assert "virality" in debug
        assert "game_design_value" in debug
        assert "risk" in debug

    def test_score_clamp(self):
        from sea_trend_insight.scorer import score_items

        items = [_item("Super gaming esport gacha challenge viral meme",
                        score=1000000, category="gaming",
                        tags=["gaming", "esport", "gacha"])]
        scored = score_items(items)
        assert scored[0].scores.relevance <= 1.0
        assert scored[0].scores.virality <= 1.0
        assert scored[0].scores.game_design_value <= 1.0


# ── Analyzer ───────────────────────────────────────────────────

class TestAnalyzer:
    def _make_scored(self, keyword="test", country="PH", category="trending",
                     gdv=0.0, relevance=0.5, source="google_trends"):
        item = ScoredItem(
            keyword=keyword, country=country, source=source, platform="google",
            category=category, title=keyword, score=100000,
        )
        item.scores = ScoreBreakdown(
            relevance=relevance, virality=0.3, game_design_value=gdv, risk=0.0,
        )
        return item

    def test_country_summaries(self):
        from sea_trend_insight.analyzer import build_country_summaries

        items = [
            self._make_scored("A", "PH"),
            self._make_scored("B", "PH"),
            self._make_scored("C", "ID"),
        ]
        summaries = build_country_summaries(items)
        assert len(summaries) == 2
        ph = [s for s in summaries if s.country == "PH"][0]
        assert ph.total_items == 2

    def test_cross_country_hotspots(self):
        from sea_trend_insight.analyzer import find_cross_country_hotspots

        items = [
            self._make_scored("Mobile Legends", "PH", "gaming", gdv=0.8),
            self._make_scored("Mobile Legends", "ID", "gaming", gdv=0.8),
            self._make_scored("Typhoon", "PH", "news"),
        ]
        hotspots = find_cross_country_hotspots(items)
        assert len(hotspots) >= 1
        assert hotspots[0]["keyword"] == "Mobile Legends"
        assert set(hotspots[0]["countries"]) == {"PH", "ID"}

    def test_gaming_hotspots(self):
        from sea_trend_insight.analyzer import find_gaming_hotspots

        items = [
            self._make_scored("MLBB", "PH", "gaming", gdv=0.8),
            self._make_scored("News", "PH", "news"),
        ]
        gaming = find_gaming_hotspots(items)
        assert len(gaming) == 1
        assert gaming[0]["keyword"] == "MLBB"

    def test_design_insights(self):
        from sea_trend_insight.analyzer import generate_design_insights

        items = [
            self._make_scored("MPL PH Season 14", "PH", "gaming", gdv=0.8),
            self._make_scored("Random news", "PH", "news", gdv=0.1),
        ]
        insights = generate_design_insights(items)
        assert len(insights) >= 1
        assert insights[0].item_keyword == "MPL PH Season 14"
        assert "电竞" in insights[0].why_notable or "游戏" in insights[0].why_notable

    def test_trend_summary(self):
        from sea_trend_insight.analyzer import build_trend_summary

        items = [
            self._make_scored("MLBB", "PH", "gaming", gdv=0.8),
            self._make_scored("MLBB", "ID", "gaming", gdv=0.8),
            self._make_scored("Typhoon", "PH", "news"),
        ]
        summary = build_trend_summary(items)
        assert len(summary.cross_country_hotspots) >= 1
        assert len(summary.gaming_hotspots) >= 1
