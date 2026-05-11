from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class SourceItem:
    source: str
    platform: str
    country: str
    title: str
    keyword: str
    url: str | None = None
    published_at: str | None = None
    raw_score: float | None = None
    language: str | None = None
    category: str | None = None
    tags: list[str] = field(default_factory=list)
    summary: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SourceItem:
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})


@dataclass
class NormalizedItem:
    keyword: str
    country: str
    source: str
    platform: str
    category: str
    title: str
    url: str | None = None
    score: float = 0.0
    language: str | None = None
    tags: list[str] = field(default_factory=list)
    summary: str | None = None
    fetched_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> NormalizedItem:
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})


@dataclass
class ScoreBreakdown:
    relevance: float = 0.0
    virality: float = 0.0
    game_design_value: float = 0.0
    risk: float = 0.0
    debug: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ScoredItem:
    keyword: str
    country: str
    source: str
    platform: str
    category: str
    title: str
    url: str | None = None
    score: float = 0.0
    language: str | None = None
    tags: list[str] = field(default_factory=list)
    summary: str | None = None
    fetched_at: str = ""
    scores: ScoreBreakdown = field(default_factory=ScoreBreakdown)
    classify_debug: dict[str, Any] = field(default_factory=dict)
    merged_from: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d

    @classmethod
    def from_normalized(cls, item: NormalizedItem) -> ScoredItem:
        return cls(
            keyword=item.keyword,
            country=item.country,
            source=item.source,
            platform=item.platform,
            category=item.category,
            title=item.title,
            url=item.url,
            score=item.score,
            language=item.language,
            tags=list(item.tags),
            summary=item.summary,
            fetched_at=item.fetched_at,
        )


@dataclass
class DesignInsight:
    item_keyword: str
    item_country: str
    why_notable: str
    player_psychology: str
    game_design_direction: str
    risk_reminder: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CountrySummary:
    country: str
    country_label: str
    total_items: int
    top_items: list[dict[str, Any]] = field(default_factory=list)
    category_counts: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TrendSummary:
    cross_country_hotspots: list[dict[str, Any]] = field(default_factory=list)
    country_unique_hotspots: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    gaming_hotspots: list[dict[str, Any]] = field(default_factory=list)
    design_insights: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


CATEGORY_LABELS = {
    "news": "重要新闻/民生",
    "gaming": "游戏相关",
    "viral": "大传播热点/梗",
    "trending": "民众热搜",
}

COUNTRY_LABELS = {
    "PH": "Philippines 菲律宾",
    "ID": "Indonesia 印尼",
    "TH": "Thailand 泰国",
}


@dataclass
class ReportSection:
    category: str
    category_label: str
    country: str
    country_label: str
    items: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RunLog:
    date: str
    started_at: str
    finished_at: str = ""
    countries: list[str] = field(default_factory=list)
    providers_status: dict[str, str] = field(default_factory=dict)
    total_items: int = 0
    items_by_country: dict[str, int] = field(default_factory=dict)
    items_by_category: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    output_files: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def save(self, path: str) -> None:
        from pathlib import Path
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False))
