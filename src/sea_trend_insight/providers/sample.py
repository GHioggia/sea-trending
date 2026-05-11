from __future__ import annotations

import json
from pathlib import Path

from sea_trend_insight.models import SourceItem
from sea_trend_insight.providers.base import TrendProvider


class SampleProvider(TrendProvider):
    name = "sample"
    platform = "sample"

    def __init__(self, sample_dir: Path | str | None = None):
        if sample_dir is None:
            self.sample_dir = Path(__file__).resolve().parents[3] / "data" / "sample"
        else:
            self.sample_dir = Path(sample_dir)

    def fetch(self, country: str, date: str) -> list[SourceItem]:
        items: list[SourceItem] = []
        for path in sorted(self.sample_dir.glob(f"*_{country}.json")):
            raw = json.loads(path.read_text())
            for entry in raw:
                items.append(SourceItem.from_dict(entry))
        return items
