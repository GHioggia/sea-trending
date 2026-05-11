from __future__ import annotations

import re
from typing import Any

from sea_trend_insight.models import NormalizedItem, ScoredItem, ScoreBreakdown

DEFAULT_WEIGHTS = {
    "relevance": {
        "raw_score_max": 500000,
        "source_weights": {
            "google_trends": 1.0,
            "google_news": 0.9,
            "gdelt": 0.8,
            "trends24": 0.7,
            "getdaytrends": 0.7,
            "kworb_youtube": 0.6,
            "google_play": 0.8,
            "appbrain": 0.7,
            "appfigures": 0.7,
            "sample": 0.5,
        },
        "multi_source_bonus": 0.15,
    },
    "virality": {
        "viral_keyword_boost": 0.3,
        "high_score_threshold": 100000,
        "high_score_boost": 0.2,
        "platform_weights": {
            "tiktok": 1.0,
            "twitter": 0.9,
            "youtube": 0.8,
            "google": 0.6,
            "android": 0.4,
        },
    },
    "game_design_value": {
        "gaming_category_base": 0.6,
        "gaming_keyword_boost": 0.2,
        "cultural_keyword_boost": 0.15,
        "viral_mechanic_boost": 0.1,
        "cultural_keywords": [
            r"festival", r"holiday", r"tradition", r"food",
            r"fashion", r"music", r"dance", r"cosplay",
            r"ramadan", r"eid", r"songkran", r"loy\s*krathong",
            r"sinulog", r"ati-atihan", r"lebaran", r"imlek",
        ],
        "viral_mechanic_keywords": [
            r"challenge", r"meme", r"trend", r"viral",
            r"dance", r"mukbang", r"unboxing",
        ],
    },
    "risk": {
        "sensitive_keywords": [
            r"death", r"suicide", r"kill", r"murder", r"bomb",
            r"terror", r"drug", r"gambling", r"sex",
            r"religion", r"political\s*crisis", r"coup",
            r"riot", r"protest", r"martial\s*law",
            r"bunuh", r"narkoba", r"judi",
            r"ฆ่า", r"ยาเสพติด", r"การพนัน",
        ],
        "controversy_keywords": [
            r"scandal", r"controversy", r"backlash", r"boycott",
            r"lawsuit", r"fraud", r"corruption",
        ],
        "sensitive_score": 0.7,
        "controversy_score": 0.4,
    },
}


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, v))


def _compile_patterns(keywords: list[str]) -> re.Pattern:
    return re.compile("|".join(keywords), re.IGNORECASE)


def score_relevance(item: ScoredItem, weights: dict[str, Any]) -> tuple[float, dict]:
    debug: dict[str, Any] = {}
    raw_max = weights.get("raw_score_max", 500000)
    source_w = weights.get("source_weights", {})

    raw_norm = min(item.score / raw_max, 1.0) if raw_max > 0 and item.score > 0 else 0.0
    source_mult = source_w.get(item.source, 0.5)
    base = raw_norm * 0.6 + source_mult * 0.4

    debug["raw_score"] = item.score
    debug["raw_normalized"] = round(raw_norm, 3)
    debug["source_weight"] = source_mult
    debug["base"] = round(base, 3)

    return _clamp(base), debug


def score_virality(item: ScoredItem, weights: dict[str, Any]) -> tuple[float, dict]:
    debug: dict[str, Any] = {}
    base = 0.0

    platform_w = weights.get("platform_weights", {})
    p_score = platform_w.get(item.platform, 0.5)
    base += p_score * 0.3
    debug["platform_weight"] = p_score

    viral_re = _compile_patterns(weights.get("viral_mechanic_keywords", DEFAULT_WEIGHTS["game_design_value"]["viral_mechanic_keywords"]))
    text = f"{item.keyword} {item.title} {item.summary or ''}"
    if viral_re.search(text):
        boost = weights.get("viral_keyword_boost", 0.3)
        base += boost
        debug["viral_keyword_match"] = True

    threshold = weights.get("high_score_threshold", 100000)
    if item.score >= threshold:
        boost = weights.get("high_score_boost", 0.2)
        ratio = min(item.score / threshold, 3.0) / 3.0
        base += boost * ratio
        debug["high_score_boost"] = round(boost * ratio, 3)

    if len(item.merged_from) > 0:
        base += 0.1 * min(len(item.merged_from), 3)
        debug["multi_source_count"] = len(item.merged_from)

    debug["total"] = round(base, 3)
    return _clamp(base), debug


def score_game_design_value(item: ScoredItem, weights: dict[str, Any]) -> tuple[float, dict]:
    debug: dict[str, Any] = {}
    base = 0.0
    text = f"{item.keyword} {item.title} {item.summary or ''} {' '.join(item.tags)}"

    if item.category == "gaming":
        gbase = weights.get("gaming_category_base", 0.6)
        base += gbase
        debug["gaming_category"] = True

    gaming_kw_re = _compile_patterns([
        r"mobile\s*legends", r"genshin", r"valorant", r"free\s*fire",
        r"pubg", r"roblox", r"minecraft", r"gacha", r"esport",
    ])
    if gaming_kw_re.search(text):
        boost = weights.get("gaming_keyword_boost", 0.2)
        base += boost
        debug["gaming_keyword_match"] = True

    cultural_patterns = weights.get("cultural_keywords", DEFAULT_WEIGHTS["game_design_value"]["cultural_keywords"])
    cultural_re = _compile_patterns(cultural_patterns)
    if cultural_re.search(text):
        boost = weights.get("cultural_keyword_boost", 0.15)
        base += boost
        debug["cultural_match"] = True

    viral_patterns = weights.get("viral_mechanic_keywords", DEFAULT_WEIGHTS["game_design_value"]["viral_mechanic_keywords"])
    vm_re = _compile_patterns(viral_patterns)
    if vm_re.search(text):
        boost = weights.get("viral_mechanic_boost", 0.1)
        base += boost
        debug["viral_mechanic_match"] = True

    debug["total"] = round(base, 3)
    return _clamp(base), debug


def score_risk(item: ScoredItem, weights: dict[str, Any]) -> tuple[float, dict]:
    debug: dict[str, Any] = {}
    text = f"{item.keyword} {item.title} {item.summary or ''}"
    risk = 0.0

    sensitive_patterns = weights.get("sensitive_keywords", DEFAULT_WEIGHTS["risk"]["sensitive_keywords"])
    sensitive_re = _compile_patterns(sensitive_patterns)
    m = sensitive_re.search(text)
    if m:
        risk = max(risk, weights.get("sensitive_score", 0.7))
        debug["sensitive_match"] = m.group()

    controversy_patterns = weights.get("controversy_keywords", DEFAULT_WEIGHTS["risk"]["controversy_keywords"])
    controversy_re = _compile_patterns(controversy_patterns)
    m = controversy_re.search(text)
    if m:
        risk = max(risk, weights.get("controversy_score", 0.4))
        debug["controversy_match"] = m.group()

    debug["risk"] = round(risk, 3)
    return _clamp(risk), debug


def score_item(item: ScoredItem, cfg_weights: dict[str, Any] | None = None) -> ScoredItem:
    w = cfg_weights or DEFAULT_WEIGHTS

    rel, rel_debug = score_relevance(item, w.get("relevance", {}))
    vir, vir_debug = score_virality(item, w.get("virality", {}))
    gdv, gdv_debug = score_game_design_value(item, w.get("game_design_value", {}))
    rsk, rsk_debug = score_risk(item, w.get("risk", {}))

    item.scores = ScoreBreakdown(
        relevance=round(rel, 3),
        virality=round(vir, 3),
        game_design_value=round(gdv, 3),
        risk=round(rsk, 3),
        debug={
            "relevance": rel_debug,
            "virality": vir_debug,
            "game_design_value": gdv_debug,
            "risk": rsk_debug,
        },
    )
    return item


def score_items(
    items: list[NormalizedItem],
    cfg_weights: dict[str, Any] | None = None,
) -> list[ScoredItem]:
    scored = [ScoredItem.from_normalized(it) for it in items]
    for item in scored:
        score_item(item, cfg_weights)
    return scored
