from __future__ import annotations

from typing import Any

from sea_trend_insight.models import CATEGORY_LABELS, COUNTRY_LABELS
from sea_trend_insight.translator import annotate_zh

CATEGORY_EMOJI = {
    "news": "📰",
    "gaming": "🎮",
    "viral": "🔥",
    "trending": "🔍",
}


def generate_broadcast(report: dict[str, Any], pages_url: str = "") -> str:
    date = report["date"]
    total = report["total_items"]
    pages_url = pages_url.rstrip("/")
    lines: list[str] = []

    lines.append(f"# SEA 趋势日报 {date}")
    lines.append("")

    cat_stats = report.get("items_by_category", {})
    country_stats = report.get("items_by_country", {})
    stat_parts = [f"共 {total} 条"]
    for c in ["PH", "ID", "TH"]:
        if c in country_stats:
            stat_parts.append(f"{c} {country_stats[c]}")
    lines.append(f"> {' | '.join(stat_parts)}")
    lines.append("")

    trend_summary = report.get("trend_summary", {})
    cross = trend_summary.get("cross_country_hotspots", [])
    if cross:
        lines.append("## 🌏 跨国共同热点")
        for h in cross[:3]:
            countries = "/".join(h["countries"])
            lines.append(f"- **{annotate_zh(h['keyword'])}** ({countries})")
        lines.append("")

    gaming_hotspots = trend_summary.get("gaming_hotspots", [])
    if gaming_hotspots:
        lines.append("## 🎮 游戏相关热点")
        for h in gaming_hotspots[:5]:
            country = h.get("country", "")
            lines.append(f"- **{annotate_zh(h['keyword'])}** ({country})")
        lines.append("")

    sections_by_country: dict[str, list[dict]] = {}
    for sec in report["sections"]:
        sections_by_country.setdefault(sec["country"], []).append(sec)

    for country in ["PH", "ID", "TH"]:
        secs = sections_by_country.get(country, [])
        if not secs:
            continue
        label = COUNTRY_LABELS.get(country, country)
        lines.append(f"## {label}")
        for sec in secs:
            cat = sec["category"]
            emoji = CATEGORY_EMOJI.get(cat, "")
            cat_label = sec["category_label"]
            items = sec["items"][:3]
            if not items:
                continue
            lines.append(f"**{emoji} {cat_label}**")
            for item in items:
                kw = item.get("keyword", item.get("title", ""))
                lines.append(f"- {annotate_zh(kw)}")
        lines.append("")

    insights = trend_summary.get("design_insights", [])
    if insights:
        lines.append("## 💡 设计洞察")
        for ins in insights[:3]:
            lines.append(f"**{annotate_zh(ins['item_keyword'])}** ({ins['item_country']})")
            lines.append(f"- 关注点: {ins['why_notable']}")
            lines.append(f"- 设计方向: {ins['game_design_direction']}")
            lines.append("")

    if pages_url:
        lines.append(f"📊 [完整报告]({pages_url}/{date}.html)")
    else:
        lines.append(f"📊 完整报告: {{GITHUB_PAGES_URL}}/{date}.html")
    lines.append("")

    text = "\n".join(lines)
    return text


def generate_broadcast_legacy(report: dict[str, Any], pages_url: str = "") -> str:
    date = report["date"]
    lines: list[str] = []
    lines.append(f"=== SEA Trend Insight {date} ===")
    lines.append("")

    sections_by_country: dict[str, list[dict]] = {}
    for sec in report["sections"]:
        sections_by_country.setdefault(sec["country"], []).append(sec)

    for country in ["PH", "ID", "TH"]:
        secs = sections_by_country.get(country, [])
        if not secs:
            continue
        label = COUNTRY_LABELS.get(country, country)
        lines.append(f"[ {label} ]")
        for sec in secs:
            cat_label = sec["category_label"]
            items = sec["items"][:5]
            if not items:
                continue
            lines.append(f"  {cat_label}:")
            for item in items:
                kw = item.get("keyword", item.get("title", ""))
                lines.append(f"    - {kw}")
        lines.append("")

    gaming_count = report.get("items_by_category", {}).get("gaming", 0)
    if gaming_count > 0:
        lines.append(f"[Game] 今日游戏相关趋势共 {gaming_count} 条")
        gaming_items = []
        for sec in report["sections"]:
            if sec["category"] == "gaming":
                for item in sec["items"][:3]:
                    gaming_items.append(
                        f"{item.get('keyword', '')} ({COUNTRY_LABELS.get(sec['country'], sec['country'])})"
                    )
        if gaming_items:
            lines.append("  热门: " + " | ".join(gaming_items))
        lines.append("")

    if pages_url:
        lines.append(f"Full report: {pages_url}/{date}.html")
    else:
        lines.append(f"Report: public/{date}.html")
    lines.append("")

    return "\n".join(lines)
