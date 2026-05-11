from __future__ import annotations

from collections import defaultdict
from difflib import SequenceMatcher
from typing import Any

from sea_trend_insight.models import (
    CATEGORY_LABELS,
    COUNTRY_LABELS,
    CountrySummary,
    DesignInsight,
    ScoredItem,
    TrendSummary,
)

INSIGHT_TEMPLATES = {
    "gaming_esport": {
        "why_notable": "电竞赛事 {keyword} 在{country_label}热度攀升，说明当地玩家对竞技赛事关注度高",
        "player_psychology": "玩家追求竞技荣誉和社群归属感，赛事期间活跃度和付费意愿通常上升",
        "game_design_direction": "可考虑在赛事期间推出限定活动/皮肤、观赛任务、竞猜玩法，借势提升活跃",
        "risk_reminder": "注意赛事版权和选手肖像权问题，避免直接使用赛事素材",
    },
    "gaming_new_release": {
        "why_notable": "{keyword} 在{country_label}引发关注，新游/大版本上线是玩家迁移窗口期",
        "player_psychology": "玩家对新内容有强烈好奇心和 FOMO 心理，容易在此期间尝试新游戏",
        "game_design_direction": "关注竞品更新节奏和卖点，考虑差异化活动策划或内容更新时机错开",
        "risk_reminder": "避免直接对标或模仿竞品内容，注意合规风险",
    },
    "gaming_generic": {
        "why_notable": "游戏相关话题 {keyword} 在{country_label}成为热搜，反映当地游戏市场活跃",
        "player_psychology": "玩家对游戏内容持续关注，有社群讨论和分享的需求",
        "game_design_direction": "可关注该话题涉及的玩法类型和受众偏好，用于后续策划参考",
        "risk_reminder": "关注话题情绪倾向，若涉及负面评价需谨慎借势",
    },
    "viral_challenge": {
        "why_notable": "传播热梗 {keyword} 在{country_label}爆发，具有跨平台传播力",
        "player_psychology": "玩家喜欢参与潮流内容，热梗激发 UGC 创作欲和社交分享需求",
        "game_design_direction": "可考虑将热梗元素融入游戏内活动、表情包或社区互动玩法",
        "risk_reminder": "热梗生命周期短，需快速决策；注意是否涉及争议内容",
    },
    "cultural_event": {
        "why_notable": "{keyword} 是{country_label}当地文化热点，反映社会关注和情绪走向",
        "player_psychology": "文化事件触发集体情绪（节日欢庆/灾害关切），玩家可能期待游戏内的呼应",
        "game_design_direction": "节日类可做限定活动/主题皮肤；灾害类宜低调，避免不当借势",
        "risk_reminder": "文化敏感度高，需经过本地化团队审核",
    },
    "news_major": {
        "why_notable": "{keyword} 是{country_label}重要新闻，可能影响玩家在线时长和消费情绪",
        "player_psychology": "重大新闻（自然灾害/政策变化）影响玩家生活，间接影响游戏行为",
        "game_design_direction": "了解当地社会背景，避免在敏感时期推送不合时宜的活动",
        "risk_reminder": "政治/灾害新闻需保持中立，不宜在游戏中直接引用",
    },
}

ESPORT_KEYWORDS = [
    "mpl", "esport", "tournament", "champion", "finals", "league",
    "pmpl", "m5", "m6",
]
RELEASE_KEYWORDS = [
    "launch", "release", "update", "version", "patch", "season",
    "5.0", "4.0", "new", "terbaru",
]
CULTURAL_KEYWORDS = [
    "festival", "holiday", "tradition", "food", "fashion", "music",
    "dance", "cosplay", "ramadan", "eid", "songkran", "sinulog",
    "christmas", "new year",
]


def _item_summary_dict(item: ScoredItem) -> dict[str, Any]:
    return {
        "keyword": item.keyword,
        "title": item.title,
        "country": item.country,
        "source": item.source,
        "category": item.category,
        "url": item.url,
        "scores": item.scores.to_dict() if item.scores else {},
    }


def _composite_score(item: ScoredItem) -> float:
    s = item.scores
    return s.relevance * 0.3 + s.virality * 0.2 + s.game_design_value * 0.4 - s.risk * 0.1


def build_country_summaries(
    items: list[ScoredItem],
    top_n: int = 10,
) -> list[CountrySummary]:
    by_country: dict[str, list[ScoredItem]] = defaultdict(list)
    for item in items:
        by_country[item.country].append(item)

    summaries = []
    for country in ["PH", "ID", "TH"]:
        citems = by_country.get(country, [])
        if not citems:
            continue
        cat_counts: dict[str, int] = defaultdict(int)
        for it in citems:
            cat_counts[it.category] += 1

        sorted_items = sorted(citems, key=_composite_score, reverse=True)
        summaries.append(CountrySummary(
            country=country,
            country_label=COUNTRY_LABELS.get(country, country),
            total_items=len(citems),
            top_items=[_item_summary_dict(it) for it in sorted_items[:top_n]],
            category_counts=dict(cat_counts),
        ))
    return summaries


def _keyword_similar(a: str, b: str) -> bool:
    na = a.lower().strip()
    nb = b.lower().strip()
    if na == nb:
        return True
    return SequenceMatcher(None, na, nb).ratio() >= 0.6


def find_cross_country_hotspots(items: list[ScoredItem]) -> list[dict[str, Any]]:
    by_keyword: dict[str, dict[str, ScoredItem]] = {}
    for item in items:
        matched_key = None
        for existing_key in by_keyword:
            if _keyword_similar(item.keyword, existing_key):
                matched_key = existing_key
                break
        if matched_key is None:
            matched_key = item.keyword
        if matched_key not in by_keyword:
            by_keyword[matched_key] = {}
        country = item.country
        if country not in by_keyword[matched_key] or _composite_score(item) > _composite_score(by_keyword[matched_key][country]):
            by_keyword[matched_key][country] = item

    hotspots = []
    for keyword, country_map in by_keyword.items():
        if len(country_map) >= 2:
            countries = sorted(country_map.keys())
            best = max(country_map.values(), key=_composite_score)
            hotspots.append({
                "keyword": keyword,
                "countries": countries,
                "country_count": len(countries),
                "best_item": _item_summary_dict(best),
                "composite_score": round(_composite_score(best), 3),
            })
    hotspots.sort(key=lambda x: x["composite_score"], reverse=True)
    return hotspots


def find_country_unique_hotspots(
    items: list[ScoredItem],
    cross_keywords: set[str],
    top_n: int = 5,
) -> dict[str, list[dict[str, Any]]]:
    by_country: dict[str, list[ScoredItem]] = defaultdict(list)
    for item in items:
        is_cross = any(_keyword_similar(item.keyword, ck) for ck in cross_keywords)
        if not is_cross:
            by_country[item.country].append(item)

    result = {}
    for country in ["PH", "ID", "TH"]:
        citems = by_country.get(country, [])
        sorted_items = sorted(citems, key=_composite_score, reverse=True)
        result[country] = [_item_summary_dict(it) for it in sorted_items[:top_n]]
    return result


def find_gaming_hotspots(items: list[ScoredItem], top_n: int = 10) -> list[dict[str, Any]]:
    gaming = [it for it in items if it.category == "gaming"]
    gaming.sort(key=_composite_score, reverse=True)
    return [_item_summary_dict(it) for it in gaming[:top_n]]


def _select_template(item: ScoredItem) -> str:
    text = f"{item.keyword} {item.title}".lower()

    if item.category == "gaming":
        if any(kw in text for kw in ESPORT_KEYWORDS):
            return "gaming_esport"
        if any(kw in text for kw in RELEASE_KEYWORDS):
            return "gaming_new_release"
        return "gaming_generic"

    if item.category == "viral":
        return "viral_challenge"

    if any(kw in text for kw in CULTURAL_KEYWORDS):
        return "cultural_event"

    return "news_major"


def generate_design_insights(
    items: list[ScoredItem],
    top_n: int = 8,
) -> list[DesignInsight]:
    candidates = [it for it in items if it.scores.game_design_value >= 0.3 or it.category == "gaming"]
    candidates.sort(key=lambda it: it.scores.game_design_value, reverse=True)
    candidates = candidates[:top_n]

    insights = []
    for item in candidates:
        template_key = _select_template(item)
        template = INSIGHT_TEMPLATES[template_key]
        country_label = COUNTRY_LABELS.get(item.country, item.country)

        fmt = {"keyword": item.keyword, "country_label": country_label}
        insights.append(DesignInsight(
            item_keyword=item.keyword,
            item_country=item.country,
            why_notable=template["why_notable"].format(**fmt),
            player_psychology=template["player_psychology"],
            game_design_direction=template["game_design_direction"],
            risk_reminder=template["risk_reminder"],
        ))

    return insights


def build_trend_summary(items: list[ScoredItem]) -> TrendSummary:
    cross_hotspots = find_cross_country_hotspots(items)
    cross_keywords = {h["keyword"] for h in cross_hotspots}
    unique_hotspots = find_country_unique_hotspots(items, cross_keywords)
    gaming_hotspots = find_gaming_hotspots(items)
    insights = generate_design_insights(items)

    return TrendSummary(
        cross_country_hotspots=cross_hotspots,
        country_unique_hotspots=unique_hotspots,
        gaming_hotspots=gaming_hotspots,
        design_insights=[ins.to_dict() for ins in insights],
    )
