import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIRS = ["data/raw", "data/normalized", "reports", "logs"]


@pytest.fixture(autouse=True)
def clean_outputs():
    for d in OUTPUT_DIRS:
        p = ROOT / d
        if p.exists():
            shutil.rmtree(p)
    public = ROOT / "public"
    if public.exists():
        shutil.rmtree(public)
    yield
    for d in OUTPUT_DIRS:
        p = ROOT / d
        if p.exists():
            shutil.rmtree(p)
    public = ROOT / "public"
    if public.exists():
        shutil.rmtree(public)


def test_sample_dry_run():
    from sea_trend_insight.cli import main

    rc = main(["run", "--date", "2026-05-09", "--sample", "--dry-run"])
    assert rc == 0

    raw_dir = ROOT / "data" / "raw" / "2026-05-09"
    assert raw_dir.exists()
    raw_files = list(raw_dir.glob("*.json"))
    assert len(raw_files) >= 3

    norm_path = ROOT / "data" / "normalized" / "2026-05-09" / "items.json"
    assert norm_path.exists()
    items = json.loads(norm_path.read_text())
    assert len(items) > 0

    countries_found = {it["country"] for it in items}
    assert countries_found == {"PH", "ID", "TH"}

    categories_found = {it["category"] for it in items}
    assert "gaming" in categories_found
    assert "news" in categories_found

    report_path = ROOT / "reports" / "2026-05-09" / "report.json"
    assert report_path.exists()
    report = json.loads(report_path.read_text())
    assert report["date"] == "2026-05-09"
    assert report["total_items"] > 0
    assert len(report["sections"]) > 0
    assert "country_summaries" in report
    assert "trend_summary" in report
    assert "dedup_log" in report

    # Check scored items have scores breakdown
    first_item = report["sections"][0]["items"][0]
    assert "scores" in first_item
    assert "relevance" in first_item["scores"]
    assert "game_design_value" in first_item["scores"]

    # Check broadcast.md generated
    broadcast_path = ROOT / "reports" / "2026-05-09" / "broadcast.md"
    assert broadcast_path.exists()
    broadcast_text = broadcast_path.read_text()
    assert "SEA" in broadcast_text

    log_path = ROOT / "logs" / "2026-05-09-run.json"
    assert log_path.exists()
    run_log = json.loads(log_path.read_text())
    assert run_log["total_items"] > 0
    assert not run_log["errors"]

    assert not (ROOT / "public" / "2026-05-09.html").exists()


def test_sample_run_with_publish():
    from sea_trend_insight.cli import main

    rc = main(["run", "--date", "2026-05-09", "--sample"])
    assert rc == 0

    public_dir = ROOT / "public"
    assert (public_dir / "2026-05-09.html").exists()
    assert (public_dir / "index.html").exists()

    html = (public_dir / "2026-05-09.html").read_text()
    assert "玩家趋势日报" in html
    assert "Philippines" in html or "菲律宾" in html
    assert "Indonesia" in html or "印尼" in html
    assert "Thailand" in html or "泰国" in html


def test_report_command():
    from sea_trend_insight.cli import main

    rc = main(["report", "--date", "2026-05-09", "--sample"])
    assert rc == 0

    report_path = ROOT / "reports" / "2026-05-09" / "report.json"
    assert report_path.exists()


def test_broadcast_command():
    from sea_trend_insight.cli import main

    main(["report", "--date", "2026-05-09", "--sample"])
    rc = main(["broadcast", "--date", "2026-05-09"])
    assert rc == 0


def test_publish_dry_run():
    from sea_trend_insight.cli import main

    main(["report", "--date", "2026-05-09", "--sample"])
    rc = main(["publish", "--date", "2026-05-09", "--dry-run"])
    assert rc == 0
    assert not (ROOT / "public" / "2026-05-09.html").exists()


def test_all_four_categories_present():
    from sea_trend_insight.cli import main

    main(["report", "--date", "2026-05-09", "--sample"])
    report_path = ROOT / "reports" / "2026-05-09" / "report.json"
    report = json.loads(report_path.read_text())
    cats = {sec["category"] for sec in report["sections"]}
    assert cats == {"news", "gaming", "viral", "trending"}


def test_classifier_keywords():
    from sea_trend_insight.classifier import classify
    from sea_trend_insight.models import NormalizedItem

    gaming = NormalizedItem(
        keyword="Mobile Legends MPL",
        country="PH", source="test", platform="test",
        category="", title="MPL PH Season 14",
    )
    assert classify(gaming) == "gaming"

    news = NormalizedItem(
        keyword="Typhoon Carina",
        country="PH", source="test", platform="test",
        category="", title="Typhoon update",
    )
    assert classify(news) == "news"

    viral = NormalizedItem(
        keyword="Dance challenge viral",
        country="PH", source="test", platform="test",
        category="", title="TikTok viral challenge",
    )
    assert classify(viral) == "viral"

    trending = NormalizedItem(
        keyword="SB19 concert",
        country="PH", source="test", platform="test",
        category="", title="SB19 PAGTATAG tour",
    )
    assert classify(trending) == "trending"
