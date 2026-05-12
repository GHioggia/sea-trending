from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sea_trend_insight.analyzer import build_country_summaries, build_trend_summary
from sea_trend_insight.classifier import classify_items, classify_with_debug
from sea_trend_insight.config import load_config, project_root
from sea_trend_insight.dedup import deduplicate
from sea_trend_insight.models import NormalizedItem, RunLog, ScoredItem, SourceItem
from sea_trend_insight.providers import LIVE_PROVIDERS
from sea_trend_insight.providers.sample import SampleProvider
from sea_trend_insight.report import build_report, save_report
from sea_trend_insight.publisher import publish, render_html
from sea_trend_insight.broadcast import generate_broadcast
from sea_trend_insight.scorer import score_items

log = logging.getLogger("sea_trend_insight")


def _normalize(item: SourceItem, now_iso: str) -> NormalizedItem:
    return NormalizedItem(
        keyword=item.keyword,
        country=item.country,
        source=item.source,
        platform=item.platform,
        category=item.category or "trending",
        title=item.title,
        url=item.url,
        score=item.raw_score or 0.0,
        language=item.language,
        tags=list(item.tags),
        summary=item.summary,
        fetched_at=now_iso,
    )


def _save_json(data: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def _setup_logging(logs_dir: Path, date: str) -> Path:
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / f"{date}-run.log"
    root = logging.getLogger("sea_trend_insight")
    if not root.handlers:
        handler = logging.FileHandler(log_file, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        root.addHandler(handler)
        root.setLevel(logging.INFO)
        console = logging.StreamHandler()
        console.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
        root.addHandler(console)
    return log_file


def _build_live_providers(cfg: dict[str, Any]) -> list:
    providers = []
    prov_cfg = cfg.get("providers", {})
    proxy = prov_cfg.get("proxy", "") or None
    for name, cls in LIVE_PROVIDERS.items():
        entry = prov_cfg.get(name, {})
        if not entry.get("enabled", False):
            continue
        kwargs: dict[str, Any] = {"proxy": proxy}
        if name == "appfigures":
            api_key = entry.get("api_key", "")
            kwargs["api_key"] = api_key if api_key else None
        providers.append(cls(**kwargs))
    return providers


def cmd_run(
    date: str,
    countries: list[str],
    sample: bool = False,
    live: bool = False,
    dry_run: bool = False,
    config_path: str | None = None,
) -> dict[str, Any]:
    cfg = load_config(config_path)
    root = project_root()
    out_cfg = cfg["output"]
    raw_dir = root / out_cfg["raw_dir"] / date
    norm_dir = root / out_cfg["normalized_dir"] / date
    reports_dir = root / out_cfg["reports_dir"]
    public_dir = root / out_cfg["public_dir"]
    logs_dir = root / out_cfg["logs_dir"]

    log_file = _setup_logging(logs_dir, date)
    now_iso = datetime.now(timezone.utc).isoformat()

    run_log = RunLog(
        date=date,
        started_at=now_iso,
        countries=list(countries),
    )

    log.info("Starting run for %s, countries=%s, sample=%s, live=%s, dry_run=%s",
             date, countries, sample, live, dry_run)

    # --- Fetch ---
    all_source_items: list[SourceItem] = []

    if sample:
        provider = SampleProvider(root / "data" / "sample")
        for country in countries:
            try:
                items = provider.fetch(country, date)
                provider.save_raw(items, raw_dir, country)
                all_source_items.extend(items)
                run_log.providers_status[f"sample_{country}"] = "ok"
                log.info("sample/%s: %d items", country, len(items))
            except Exception as e:
                run_log.providers_status[f"sample_{country}"] = "failed"
                run_log.errors.append(f"sample/{country}: {e}")
                log.error("sample/%s failed: %s", country, e)

    if live:
        live_providers = _build_live_providers(cfg)
        if not live_providers:
            log.warning("No live providers enabled in config")
            run_log.errors.append("No live providers enabled")
        for prov in live_providers:
            for country in countries:
                key = f"{prov.name}_{country}"
                try:
                    items = prov.fetch(country, date)
                    if items:
                        prov.save_raw(items, raw_dir, country)
                        all_source_items.extend(items)
                    run_log.providers_status[key] = "ok"
                    log.info("%s/%s: %d items", prov.name, country, len(items))
                except Exception as e:
                    run_log.providers_status[key] = "failed"
                    run_log.errors.append(f"{prov.name}/{country}: {e}")
                    log.error("%s/%s failed: %s", prov.name, country, e)

    if not all_source_items:
        log.error("No items fetched, aborting")
        run_log.finished_at = datetime.now(timezone.utc).isoformat()
        run_log.save(str(logs_dir / f"{date}-run.json"))
        return run_log.to_dict()

    # --- Normalize ---
    normalized = [_normalize(item, now_iso) for item in all_source_items]

    # --- Dedup ---
    analysis_cfg = cfg.get("analysis", {})
    dedup_cfg = analysis_cfg.get("dedup", {})
    threshold = dedup_cfg.get("title_similarity_threshold", 0.7)
    deduped, dedup_log = deduplicate(normalized, title_threshold=threshold)
    log.info("Dedup: %d → %d items (%d merged)", len(normalized), len(deduped), len(dedup_log))

    # --- Classify ---
    llm_cfg = cfg.get("llm", {})
    use_llm = llm_cfg.get("enabled", False)
    classify_debug_map: dict[int, dict] = {}

    if use_llm and llm_cfg.get("classify", {}).get("enabled", True):
        from sea_trend_insight.classifier import classify_batch_llm
        llm_results = classify_batch_llm(deduped, llm_cfg)
        log.info("LLM classify: %d/%d items classified", len(llm_results), len(deduped))
    else:
        llm_results = {}

    for i, item in enumerate(deduped):
        if i in llm_results:
            cat, debug = llm_results[i]
        else:
            cat, debug = classify_with_debug(item)
        item.category = cat
        classify_debug_map[i] = debug

    norm_path = norm_dir / "items.json"
    _save_json([it.to_dict() for it in deduped], norm_path)
    run_log.output_files.append(str(norm_path))
    log.info("Normalized %d items → %s", len(deduped), norm_path)

    # --- Score ---
    scoring_cfg = cfg.get("scoring", None)
    scored = score_items(deduped, scoring_cfg)
    for i, item in enumerate(scored):
        if i in classify_debug_map:
            item.classify_debug = classify_debug_map[i]
    log.info("Scored %d items", len(scored))

    # --- Analyze ---
    country_summaries = build_country_summaries(
        scored,
        top_n=analysis_cfg.get("country_summary", {}).get("top_n", 10),
    )
    trend_summary = build_trend_summary(scored)

    if use_llm and llm_cfg.get("insights", {}).get("enabled", True):
        from sea_trend_insight.analyzer import generate_design_insights_llm
        top_n_insights = analysis_cfg.get("design_insights", {}).get("top_n", 8)
        llm_insights = generate_design_insights_llm(scored, llm_cfg, top_n=top_n_insights)
        if llm_insights:
            trend_summary.design_insights = [ins.to_dict() for ins in llm_insights]
            log.info("LLM insights: %d generated", len(llm_insights))

    log.info("Analysis complete: %d country summaries, %d cross-country hotspots, %d insights",
             len(country_summaries), len(trend_summary.cross_country_hotspots),
             len(trend_summary.design_insights))

    # --- Report ---
    report = build_report(
        scored, date,
        country_summaries=[cs.to_dict() for cs in country_summaries],
        trend_summary=trend_summary.to_dict(),
        dedup_log=dedup_log,
    )
    report_path = save_report(report, reports_dir, date)
    run_log.output_files.append(str(report_path))
    log.info("Report saved → %s", report_path)

    # --- Finalize run_log (before publish, so HTML can use it) ---
    run_log.total_items = len(scored)
    for it in scored:
        run_log.items_by_country[it.country] = run_log.items_by_country.get(it.country, 0) + 1
        run_log.items_by_category[it.category] = run_log.items_by_category.get(it.category, 0) + 1
    run_log.finished_at = datetime.now(timezone.utc).isoformat()
    run_log_dict = run_log.to_dict()

    # --- Publish ---
    if not dry_run:
        archive_dir = root / cfg["publish"].get("archive_dir", "public/archive")
        written = publish(report, public_dir, archive_dir, run_log=run_log_dict)
        run_log.output_files.extend(written)
        log.info("Published %d files to %s", len(written), public_dir)
    else:
        html = render_html(report, run_log=run_log_dict)
        html_path = reports_dir / date / f"{date}.html"
        html_path.write_text(html)
        run_log.output_files.append(str(html_path))
        log.info("dry-run: HTML saved → %s (not published)", html_path)

    # --- Broadcast ---
    pages_url = cfg["publish"].get("pages_base_url", "").rstrip("/")
    broadcast_text = generate_broadcast(report, pages_url)
    broadcast_dir = reports_dir / date
    broadcast_dir.mkdir(parents=True, exist_ok=True)
    broadcast_path = broadcast_dir / "broadcast.md"
    broadcast_path.write_text(broadcast_text)
    run_log.output_files.append(str(broadcast_path))
    print("\n" + broadcast_text)

    # --- Save run log ---
    run_log.save(str(logs_dir / f"{date}-run.json"))
    log.info("Run complete: %d items, log → %s", len(scored), log_file)

    return run_log.to_dict()


def cmd_report(
    date: str,
    countries: list[str],
    sample: bool = False,
    live: bool = False,
    config_path: str | None = None,
) -> dict[str, Any]:
    return cmd_run(date, countries, sample=sample, live=live, dry_run=True, config_path=config_path)


def cmd_broadcast(date: str, config_path: str | None = None) -> str:
    cfg = load_config(config_path)
    root = project_root()
    report_path = root / cfg["output"]["reports_dir"] / date / "report.json"
    if not report_path.exists():
        raise FileNotFoundError(f"No report found at {report_path}. Run 'report' first.")
    report = json.loads(report_path.read_text())
    pages_url = cfg["publish"].get("pages_base_url", "").rstrip("/")
    text = generate_broadcast(report, pages_url)
    print(text)
    return text


def cmd_publish(
    date: str,
    dry_run: bool = False,
    commit: bool = False,
    push: bool = False,
    config_path: str | None = None,
) -> list[str]:
    cfg = load_config(config_path)
    root = project_root()
    pub_mode = cfg.get("publish", {}).get("mode", "files")

    if pub_mode == "docs":
        return _cmd_publish_docs(date, dry_run=dry_run, commit=commit, push=push, cfg=cfg, root=root)

    # Legacy file-copy mode (no git)
    report_path = root / cfg["output"]["reports_dir"] / date / "report.json"
    if not report_path.exists():
        raise FileNotFoundError(f"No report found at {report_path}. Run 'report' first.")
    report = json.loads(report_path.read_text())
    run_log_path = root / cfg["output"]["logs_dir"] / f"{date}-run.json"
    run_log_dict = json.loads(run_log_path.read_text()) if run_log_path.exists() else None

    if dry_run:
        html = render_html(report, run_log=run_log_dict)
        print(f"[dry-run] Would publish {date}.html ({len(html)} bytes)")
        return []

    public_dir = root / cfg["output"]["public_dir"]
    archive_dir = root / cfg["publish"].get("archive_dir", "archive")
    return publish(report, public_dir, archive_dir, run_log=run_log_dict)


def _cmd_publish_docs(
    date: str,
    dry_run: bool,
    commit: bool,
    push: bool,
    cfg: dict,
    root: Path,
) -> list[str]:
    from sea_trend_insight.git_publisher import (
        check_preconditions,
        dry_run_plan,
        do_commit,
        do_push,
        working_tree_summary,
    )

    pub_cfg = cfg.get("publish", {})
    pages_url = pub_cfg.get("pages_base_url", "").rstrip("/")
    reports_dir = root / cfg["output"]["reports_dir"]

    # --- Precondition checks ---
    errors = check_preconditions(date, root, cfg)
    if errors:
        print("Precondition check failed:")
        for e in errors:
            print(f"  ✗ {e}")
        if "Not a git repository" in "\n".join(errors):
            print()
            print("To initialise a git repo and link it to GitHub:")
            print("  git init")
            print("  git remote add origin https://github.com/GHioggia/sea-trending.git")
            print("  git checkout -b main")
        return []

    tree = working_tree_summary(root)
    print(f"Working tree: {tree}")

    # --- Dry-run (default) ---
    if dry_run:
        actions = dry_run_plan(date, root, cfg)
        print(f"\n[dry-run] Actions for publish --date {date}:\n")
        for a in actions:
            print(f"  {a}")
        print()
        return []

    # --- Commit ---
    if commit:
        pub_log = do_commit(date, root, cfg)
        if pub_log.get("errors"):
            print("Commit failed:")
            for e in pub_log["errors"]:
                print(f"  ✗ {e}")
            return []

        print("Committed successfully:")
        for a in pub_log.get("actions", []):
            print(f"  ✓ {a}")
        if pub_log.get("commit"):
            print(f"  commit: {pub_log['commit']}")
        if pub_log.get("pages_url"):
            print(f"  URL: {pub_log['pages_url']}")

        # Write publish-log.json
        log_dir = reports_dir / date
        log_dir.mkdir(parents=True, exist_ok=True)
        pub_log_path = log_dir / "publish-log.json"
        pub_log_path.write_text(json.dumps(pub_log, indent=2, ensure_ascii=False))
        print(f"  log: {pub_log_path.relative_to(root)}")

        # Write/update broadcast.md with final URL
        report_path = root / cfg["output"]["reports_dir"] / date / "report.json"
        if report_path.exists():
            report = json.loads(report_path.read_text())
            bc_text = generate_broadcast(report, pub_log.get("pages_url") or pages_url)
            bc_path = log_dir / "broadcast.md"
            bc_path.write_text(bc_text)
            print(f"  broadcast: {bc_path.relative_to(root)}")

        # --- Push ---
        if push:
            print("\nPushing to remote…")
            push_log = do_push(root)
            if push_log.get("success"):
                print(f"  ✓ pushed to {push_log['remote']}/{push_log['branch']}")
            else:
                print(f"  ✗ push failed: {push_log.get('error', '')}")
            pub_log["push"] = push_log
            pub_log_path.write_text(json.dumps(pub_log, indent=2, ensure_ascii=False))

        return [str(pub_log_path)]

    return []
