from __future__ import annotations

import re
from difflib import SequenceMatcher

from sea_trend_insight.models import NormalizedItem


def _normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _title_similar(a: str, b: str, threshold: float = 0.7) -> bool:
    na, nb = _normalize_text(a), _normalize_text(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    return SequenceMatcher(None, na, nb).ratio() >= threshold


def _keyword_match(a: str, b: str) -> bool:
    na, nb = _normalize_text(a), _normalize_text(b)
    if not na or not nb:
        return False
    return na == nb


GENERIC_URL_PATTERNS = [
    "trends.google.com/trending",
    "news.google.com/rss",
    "news.google.com/home",
]


def _is_generic_url(url: str) -> bool:
    for pattern in GENERIC_URL_PATTERNS:
        if pattern in url:
            return True
    return False


def _url_match(a: str | None, b: str | None) -> bool:
    if not a or not b:
        return False
    if _is_generic_url(a) or _is_generic_url(b):
        return False
    a = re.sub(r"[?#].*$", "", a.rstrip("/"))
    b = re.sub(r"[?#].*$", "", b.rstrip("/"))
    return a == b


def _pick_best(group: list[NormalizedItem]) -> NormalizedItem:
    return max(group, key=lambda it: (it.score, len(it.summary or ""), len(it.title)))


def deduplicate(
    items: list[NormalizedItem],
    title_threshold: float = 0.7,
) -> tuple[list[NormalizedItem], list[dict]]:
    if not items:
        return [], []

    groups: list[list[int]] = []
    assigned: set[int] = set()

    for i in range(len(items)):
        if i in assigned:
            continue
        group = [i]
        assigned.add(i)
        for j in range(i + 1, len(items)):
            if j in assigned:
                continue
            if items[i].country != items[j].country:
                continue
            if _url_match(items[i].url, items[j].url):
                group.append(j)
                assigned.add(j)
            elif _keyword_match(items[i].keyword, items[j].keyword):
                group.append(j)
                assigned.add(j)
            elif _title_similar(items[i].title, items[j].title, title_threshold):
                group.append(j)
                assigned.add(j)
        groups.append(group)

    result: list[NormalizedItem] = []
    merge_log: list[dict] = []

    for group in groups:
        group_items = [items[idx] for idx in group]
        best = _pick_best(group_items)
        if len(group) > 1:
            sources = list({it.source for it in group_items})
            merge_log.append({
                "kept": best.keyword,
                "merged_count": len(group),
                "sources": sources,
                "merged_titles": [it.title for it in group_items if it is not best],
            })
        result.append(best)

    return result, merge_log
