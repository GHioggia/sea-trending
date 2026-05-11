from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from sea_trend_insight.models import (
    CATEGORY_LABELS,
    COUNTRY_LABELS,
    ScoredItem,
    NormalizedItem,
    ReportSection,
)


def build_report(
    items: list[ScoredItem] | list[NormalizedItem],
    date: str,
    country_summaries: list[dict[str, Any]] | None = None,
    trend_summary: dict[str, Any] | None = None,
    dedup_log: list[dict] | None = None,
) -> dict[str, Any]:
    by_country_cat: dict[str, dict[str, list]] = defaultdict(
        lambda: defaultdict(list)
    )
    for item in items:
        by_country_cat[item.country][item.category].append(item)

    sections: list[dict[str, Any]] = []
    category_order = ["news", "gaming", "viral", "trending"]
    country_order = ["PH", "ID", "TH"]

    for country in country_order:
        if country not in by_country_cat:
            continue
        for cat in category_order:
            cat_items = by_country_cat[country].get(cat, [])
            if not cat_items:
                continue
            section = ReportSection(
                category=cat,
                category_label=CATEGORY_LABELS.get(cat, cat),
                country=country,
                country_label=COUNTRY_LABELS.get(country, country),
                items=[it.to_dict() for it in cat_items],
            )
            sections.append(section.to_dict())

    stats: dict[str, int] = {}
    for cat in category_order:
        stats[cat] = sum(
            len(by_country_cat[c].get(cat, [])) for c in by_country_cat
        )

    report: dict[str, Any] = {
        "date": date,
        "total_items": len(items),
        "items_by_country": {
            c: sum(len(v) for v in cats.values())
            for c, cats in by_country_cat.items()
        },
        "items_by_category": stats,
        "sections": sections,
    }

    if country_summaries is not None:
        report["country_summaries"] = country_summaries
    if trend_summary is not None:
        report["trend_summary"] = trend_summary
    if dedup_log is not None:
        report["dedup_log"] = dedup_log

    return report


def save_report(report: dict[str, Any], reports_dir: Path, date: str) -> Path:
    out = reports_dir / date
    out.mkdir(parents=True, exist_ok=True)
    path = out / "report.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    return path
