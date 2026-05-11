from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path

from sea_trend_insight.models import SourceItem


class TrendProvider(ABC):
    name: str
    platform: str

    @abstractmethod
    def fetch(self, country: str, date: str) -> list[SourceItem]:
        ...

    def save_raw(self, items: list[SourceItem], out_dir: Path, country: str) -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{self.name}_{country}.json"
        data = [item.to_dict() for item in items]
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        return path
