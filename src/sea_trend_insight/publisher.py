from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from sea_trend_insight.models import CATEGORY_LABELS, COUNTRY_LABELS
from sea_trend_insight.translator import annotate_zh

ITEMS_PER_CATEGORY = 3

CAT_EMOJI = {
    "news": "📰",
    "gaming": "🎮",
    "viral": "🔥",
    "trending": "🔍",
}

CATEGORY_ORDER = [
    {"key": "news", "label": "重要新闻/民生", "emoji": "📰"},
    {"key": "gaming", "label": "游戏相关", "emoji": "🎮"},
    {"key": "viral", "label": "大传播热点/梗", "emoji": "🔥"},
    {"key": "trending", "label": "民众热搜", "emoji": "🔍"},
]

COUNTRY_ORDER = [
    {"code": "PH", "label": COUNTRY_LABELS.get("PH", "Philippines")},
    {"code": "ID", "label": COUNTRY_LABELS.get("ID", "Indonesia")},
    {"code": "TH", "label": COUNTRY_LABELS.get("TH", "Thailand")},
]

RISK_KEYWORDS_MAP = {
    "typhoon": ("🌊", "自然灾害"),
    "flood": ("🌊", "自然灾害"),
    "earthquake": ("🌊", "自然灾害"),
    "tsunami": ("🌊", "自然灾害"),
    "election": ("🗳️", "政治事件"),
    "pemilu": ("🗳️", "政治事件"),
    "president": ("🗳️", "政治事件"),
    "government": ("🗳️", "政治事件"),
    "drug": ("⚠️", "社会敏感"),
    "crime": ("⚠️", "社会敏感"),
    "death": ("⚠️", "社会敏感"),
    "protest": ("⚠️", "社会敏感"),
    "inflation": ("💰", "民生压力"),
    "harga": ("💰", "民生压力"),
    "price": ("💰", "民生压力"),
    "poverty": ("💰", "民生压力"),
}


def _build_grid(sections: list[dict], n: int = ITEMS_PER_CATEGORY) -> dict[str, dict[str, list]]:
    grid: dict[str, dict[str, list]] = {}
    for cat_info in CATEGORY_ORDER:
        cat = cat_info["key"]
        grid[cat] = {}
        for c_info in COUNTRY_ORDER:
            code = c_info["code"]
            grid[cat][code] = []

    for sec in sections:
        cat = sec["category"]
        country = sec["country"]
        if cat not in grid:
            continue
        items = sec["items"][:n]
        annotated = []
        for it in items:
            it = dict(it)
            it["keyword_zh"] = _zh_part(it.get("keyword", ""))
            if "scores" not in it:
                it["scores"] = {"relevance": 0, "virality": 0, "game_design_value": 0, "risk": 0}
            annotated.append(it)
        while len(annotated) < n:
            annotated.append(None)
        grid[cat][country] = annotated

    return grid


def _zh_part(keyword: str) -> str:
    annotated = annotate_zh(keyword)
    if "（" in annotated and annotated != keyword:
        return annotated.split("（", 1)[1].rstrip("）")
    return ""


def _build_run_meta(run_log: dict[str, Any] | None) -> dict[str, Any] | None:
    if not run_log:
        return None
    providers_status = run_log.get("providers_status", {})
    seen_names: dict[str, str] = {}
    for key, status in providers_status.items():
        parts = key.rsplit("_", 1)
        name = parts[0] if len(parts) > 1 else key
        if name not in seen_names:
            seen_names[name] = status
        elif status != "ok":
            seen_names[name] = status

    providers = []
    for name, status in seen_names.items():
        css = "ok" if status == "ok" else ("fail" if "fail" in status else "skip")
        display = name.replace("_", " ").title()
        if status == "ok":
            status_text = "✓ 正常"
            css_td = "status-ok"
        elif "fail" in status or "error" in status:
            status_text = "✗ 失败"
            css_td = "status-fail"
        else:
            status_text = "— " + status
            css_td = "status-disabled"
        providers.append({
            "name": name,
            "display_name": display,
            "status": status,
            "css_class": css,
            "css_class_td": css_td,
            "status_text": status_text,
            "note": "",
        })

    ok_count = sum(1 for p in providers if p["status"] == "ok")
    return {
        "providers": providers,
        "ok_count": ok_count,
        "total_providers": len(providers),
        "errors": run_log.get("errors", []),
        "started_at": run_log.get("started_at", ""),
        "finished_at": run_log.get("finished_at", ""),
    }


def _build_risk_items(sections: list[dict]) -> list[dict]:
    risk_items = []
    for sec in sections:
        for it in sec["items"]:
            scores = it.get("scores", {})
            risk_val = scores.get("risk", 0)
            if risk_val > 0:
                kw_lower = it.get("keyword", "").lower()
                icon, label = "⚠️", "风险话题"
                for kw, (ic, lb) in RISK_KEYWORDS_MAP.items():
                    if kw in kw_lower:
                        icon, label = ic, lb
                        break
                risk_items.append({
                    "icon": icon,
                    "label": f"{label} — {annotate_zh(it.get('keyword', ''))}",
                    "country": sec["country"],
                    "detail": it.get("summary", "") or it.get("title", ""),
                    "risk": risk_val,
                })
    risk_items.sort(key=lambda x: x["risk"], reverse=True)
    return risk_items


def _enrich_insights(insights: list[dict], sections: list[dict]) -> list[dict]:
    cat_map: dict[str, str] = {}
    for sec in sections:
        for it in sec["items"]:
            cat_map[it.get("keyword", "")] = sec["category"]

    enriched = []
    for ins in insights:
        ins = dict(ins)
        ins["item_category"] = cat_map.get(ins.get("item_keyword", ""), "trending")
        enriched.append(ins)
    return enriched


from urllib.parse import quote as _urlquote

def _get_env() -> Environment:
    templates_dir = Path(__file__).resolve().parents[2] / "templates"
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=False,
    )
    env.filters["urlquote"] = _urlquote
    return env


def render_html(report: dict[str, Any], run_log: dict[str, Any] | None = None) -> str:
    env = _get_env()
    tmpl = env.get_template("daily_report.html")

    sections = report.get("sections", [])
    trend_summary = report.get("trend_summary", {})
    country_summaries = report.get("country_summaries", [])
    cross_hotspots = trend_summary.get("cross_country_hotspots", [])
    raw_insights = trend_summary.get("design_insights", [])
    insights = _enrich_insights(raw_insights, sections)

    grid = _build_grid(sections, ITEMS_PER_CATEGORY)
    run_meta = _build_run_meta(run_log)
    risk_items = _build_risk_items(sections)

    for cs in country_summaries:
        for it in cs.get("top_items", []):
            it["keyword_zh"] = _zh_part(it.get("keyword", ""))

    return tmpl.render(
        report=report,
        country_summaries=country_summaries,
        cross_hotspots=cross_hotspots,
        insights=insights,
        risk_items=risk_items,
        grid=grid,
        countries=COUNTRY_ORDER,
        categories=CATEGORY_ORDER,
        cat_emoji=CAT_EMOJI,
        run_meta=run_meta,
        zh=annotate_zh,
    )


INDEX_TEMPLATE = """\
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SEA 玩家趋势日报</title>
<style>
body{{font-family:-apple-system,sans-serif;background:#0f1117;color:#e4e4e7;max-width:600px;margin:2rem auto;padding:0 1rem}}
h1{{margin-bottom:1rem}}
a{{color:#60a5fa}}
.latest{{font-size:1.1rem;margin-bottom:2rem}}
</style>
</head>
<body>
<h1>SEA 玩家趋势日报</h1>
<div class="latest">Latest: <a href="{date}.html">{date}</a></div>
</body>
</html>
"""


def publish(
    report: dict[str, Any],
    public_dir: Path,
    archive_dir: Path | None = None,
    run_log: dict[str, Any] | None = None,
) -> list[str]:
    date = report["date"]
    public_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    if archive_dir:
        archive_dir.mkdir(parents=True, exist_ok=True)
        index_path = public_dir / "index.html"
        if index_path.exists():
            ts = datetime.now().strftime("%Y%m%d%H%M%S")
            shutil.copy2(index_path, archive_dir / f"index_{ts}.html")
        existing = public_dir / f"{date}.html"
        if existing.exists():
            ts = datetime.now().strftime("%Y%m%d%H%M%S")
            shutil.copy2(existing, archive_dir / f"{date}_{ts}.html")

    html = render_html(report, run_log)
    daily_path = public_dir / f"{date}.html"
    daily_path.write_text(html)
    written.append(str(daily_path))

    index_html = INDEX_TEMPLATE.format(date=date)
    index_path = public_dir / "index.html"
    index_path.write_text(index_html)
    written.append(str(index_path))

    return written
