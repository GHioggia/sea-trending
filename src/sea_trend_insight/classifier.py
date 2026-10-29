from __future__ import annotations

import json
import logging
import re
from typing import Any

from sea_trend_insight.models import NormalizedItem

log = logging.getLogger("sea_trend_insight")

GAMING_KEYWORDS = [
    r"mobile\s*legends", r"\bmlbb\b", r"\bmpl\b", r"genshin", r"valorant",
    r"free\s*fire", r"\brov\b", r"ragnarok", r"dota", r"league\s*of\s*legends",
    r"\blol\b", r"pubg", r"call\s*of\s*duty", r"\bcod\b", r"minecraft",
    r"roblox", r"fortnite", r"apex\s*legends", r"honkai", r"wuthering",
    r"zenless", r"\bnikke\b", r"tower\s*of\s*fantasy", r"esport",
    r"gaming", r"playstation", r"\bps5\b", r"nintendo",
    r"switch\s*2", r"xbox", r"steam", r"epic\s*games", r"gacha",
    r"battle\s*royale", r"mmorpg", r"rpg\s*game", r"arena\s*of\s*valor",
    r"เกม", r"เกมมือถือ", r"\bmabar\b", r"\bgim\b",
]

GAMING_STRONG_KEYWORDS = [
    r"mobile\s*legends", r"\bmlbb\b", r"\bmpl\b", r"genshin", r"valorant",
    r"free\s*fire", r"ragnarok", r"dota", r"league\s*of\s*legends",
    r"pubg", r"call\s*of\s*duty", r"minecraft", r"roblox", r"fortnite",
    r"apex\s*legends", r"honkai", r"wuthering", r"zenless", r"\bnikke\b",
    r"tower\s*of\s*fantasy", r"esport", r"gacha", r"battle\s*royale",
    r"mmorpg", r"arena\s*of\s*valor", r"เกมมือถือ",
]

# Game, match and play also describe sports, theatre and everyday activities.
# They are diagnostic matches only, never sufficient evidence of video games.
_AMBIGUOUS_GAME_RE = re.compile(r"\b(?:games?|match(?:es)?|play)\b", re.IGNORECASE)
_VIDEO_GAME_RE = re.compile(
    r"\b(?:video\s*games?|(?:pc|console|mobile)\s+games?|gameplay)\b",
    re.IGNORECASE,
)
_GAME_RELEASE_RE = re.compile(
    r"\b(?:new\s+)?game\s+(?:(?:is|was)\s+)?"
    r"(?:launch(?:es|ed)?|releas(?:e[ds]?|ing))\b"
    r"|\b(?:launch(?:es|ed)?|releas(?:e[ds]?|ing))\s+(?:a\s+)?(?:new\s+)?game\b",
    re.IGNORECASE,
)
# Only suppress generic release wording, not explicit video-game or title evidence:
# e.g. an NBA mobile game or a Roblox basketball match is still gaming.
_SPORTS_RE = re.compile(
    r"\b(?:nba|wnba|nfl|nhl|mlb|fifa|uefa|pba|uaap|ncaa|ipl|"
    r"lakers|celtics|warriors|basketball|football|soccer|baseball|"
    r"volleyball|cricket|tennis|badminton|premier\s+league|world\s+cup)\b",
    re.IGNORECASE,
)

NEWS_KEYWORDS = [
    r"typhoon", r"earthquake", r"flood", r"election", r"president",
    r"government", r"economy", r"gdp", r"inflation", r"policy",
    r"minister", r"pandemic", r"covid", r"health", r"education",
    r"infrastructure", r"tax", r"subsidy", r"poverty", r"crime",
    r"pemilu", r"pemerintah", r"banjir", r"gempa", r"ekonomi",
    r"รัฐบาล", r"น้ำท่วม", r"แผ่นดินไหว", r"เศรษฐกิจ", r"ค่าไฟ",
    r"philhealth", r"pagasa", r"edsa", r"mrt\b", r"lrt\b",
    r"batas\s*pambansa", r"harga\s*beras", r"bbm\b",
    r"power\s*outage", r"transport", r"\bdemo\b", r"harga\b",
    r"nikkei", r"stock\s*market", r"central\s*bank",
]

VIRAL_KEYWORDS = [
    r"\bmeme\b", r"viral", r"challenge", r"trend(?:ing)?\s*(?:video|audio|sound)",
    r"tiktok\s*trend", r"dance\s*challenge", r"mukbang", r"asmr",
    r"citayam", r"fashion\s*week", r"cosplay\s*viral", r"prank",
    r"reaction\s*video", r"street\s*food\s*viral", r"unboxing",
    r"\bbl\s*drama", r"\bbl\s*series", r"fan\s*cam", r"fancam",
    r"\bhorror\b", r"\bghost\b", r"\bhaunted\b", r"\bhoror\b",
    r"\bhantu\b", r"ผี", r"ดราม่า",
]

_GAMING_RE = re.compile("|".join(GAMING_KEYWORDS), re.IGNORECASE)
_GAMING_STRONG_RE = re.compile("|".join(GAMING_STRONG_KEYWORDS), re.IGNORECASE)
_NEWS_RE = re.compile("|".join(NEWS_KEYWORDS), re.IGNORECASE)
_VIRAL_RE = re.compile("|".join(VIRAL_KEYWORDS), re.IGNORECASE)

SOURCE_GAMING = {"google_play", "appbrain", "appfigures"}
SOURCE_NEWS_PRIORITY = {"gdelt", "google_news"}


def classify(item: NormalizedItem) -> str:
    return classify_with_debug(item)[0]


def classify_with_debug(item: NormalizedItem) -> tuple[str, dict[str, Any]]:
    # Preserve field boundaries so a keyword ending in 'game' and a title
    # starting with 'released' cannot accidentally form a release phrase.
    text = " | ".join([item.keyword, item.title, item.summary or "", *item.tags])
    debug: dict[str, Any] = {"source": item.source}

    if item.source in SOURCE_GAMING:
        debug["reason"] = f"source '{item.source}' is a gaming platform"
        return "gaming", debug

    strong_matches = _GAMING_STRONG_RE.findall(text)
    weak_matches = _GAMING_RE.findall(text)
    ambiguous_matches = _AMBIGUOUS_GAME_RE.findall(text)
    sports_matches = _SPORTS_RE.findall(text)
    video_game_matches = _VIDEO_GAME_RE.findall(text)
    release_matches = _GAME_RELEASE_RE.findall(text)
    context_matches = video_game_matches + (release_matches if not sports_matches else [])
    news_matches = _NEWS_RE.findall(text)
    viral_matches = _VIRAL_RE.findall(text)

    debug["matches"] = {
        "gaming_strong": strong_matches,
        "gaming_weak": weak_matches + context_matches,
        "ambiguous_game": ambiguous_matches,
        "sports": sports_matches,
        "game_release": release_matches,
        "news": news_matches,
        "viral": viral_matches,
    }
    if ambiguous_matches:
        debug["game_context"] = (
            "explicit video-game context" if video_game_matches else
            "sports context blocks generic game release" if sports_matches and release_matches else
            "sports context without video-game evidence" if sports_matches else
            "game release context" if release_matches else
            "ambiguous words without video-game context"
        )

    if strong_matches:
        debug["reason"] = f"strong gaming keyword: {strong_matches[0]}"
        return "gaming", debug

    if item.source in SOURCE_NEWS_PRIORITY:
        if news_matches:
            debug["reason"] = f"news source '{item.source}' + news keyword: {news_matches[0]}"
            return "news", debug
        if weak_matches or context_matches:
            debug["reason"] = f"gaming keyword in news source: {(weak_matches + context_matches)[0]}"
            return "gaming", debug
        if viral_matches:
            debug["reason"] = f"viral keyword in news source: {viral_matches[0]}"
            return "viral", debug
        debug["reason"] = f"default news for source '{item.source}'"
        return "news", debug

    all_gaming = weak_matches + context_matches
    if all_gaming and not news_matches:
        debug["reason"] = f"gaming keyword without news context: {all_gaming[0]}"
        return "gaming", debug
    if news_matches:
        debug["reason"] = f"news keyword: {news_matches[0]}"
        return "news", debug
    if viral_matches:
        debug["reason"] = f"viral keyword: {viral_matches[0]}"
        return "viral", debug

    debug["reason"] = "no keyword match → default trending"
    return "trending", debug


def classify_items(items: list[NormalizedItem]) -> list[NormalizedItem]:
    for item in items:
        item.category = classify(item)
    return items


def classify_batch_llm(
    items: list[NormalizedItem],
    llm_cfg: dict,
) -> dict[int, tuple[str, dict]]:
    """Batch-classify items via LLM. Returns {index: (category, debug)}.

    Items missing from the result should fall back to rule-based classify.
    """
    from sea_trend_insight.llm import call_json

    batch_size = llm_cfg.get("classify", {}).get("batch_size", 50)
    results: dict[int, tuple[str, dict]] = {}
    valid_cats = {"gaming", "news", "viral", "trending"}

    for start in range(0, len(items), batch_size):
        batch = items[start : start + batch_size]
        entries = [
            {
                "id": start + i,
                "keyword": item.keyword,
                "title": item.title,
                "source": item.source,
                "platform": item.platform,
                "country": item.country,
                "language": item.language or "",
                "tags": item.tags,
            }
            for i, item in enumerate(batch)
        ]

        prompt = (
            "将以下东南亚热搜条目分类为四个类别之一：\n"
            "- gaming: 游戏相关（具体游戏名、电竞赛事、应用商店游戏等）\n"
            "- news: 重要新闻/民生（政治、经济、灾害、政策等）\n"
            "- viral: 大传播热点/梗（挑战、表情包、病毒视频、网红事件等）\n"
            "- trending: 民众热搜（不属于上述三类的其他热搜）\n\n"
            "条目来自菲律宾(PH)、印尼(ID)、泰国(TH)，内容可能包含英语、印尼语、泰语、菲律宾语。\n"
            "返回 JSON 数组，格式：\n"
            '[{"id": <原id>, "category": "<分类>", "reason": "<一句话理由>"}]\n\n'
            f"条目：\n{json.dumps(entries, ensure_ascii=False)}"
        )

        try:
            parsed = call_json(
                [{"role": "user", "content": prompt}],
                llm_cfg,
                temperature=0.1,
            )
            for row in parsed:
                idx = row.get("id")
                if idx is None:
                    continue
                cat = row.get("category", "trending")
                if cat not in valid_cats:
                    cat = "trending"
                results[idx] = (cat, {"source": "llm", "reason": row.get("reason", "")})
        except Exception as e:
            log.warning(
                "LLM classify failed for batch %d-%d: %s",
                start, start + len(batch), e,
            )

    return results
