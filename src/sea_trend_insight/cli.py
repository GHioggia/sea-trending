from __future__ import annotations

import argparse
import sys
from datetime import date


def _today() -> str:
    return date.today().isoformat()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sea_trend_insight", description="SEA Trend Insight CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    # --- run ---
    p_run = sub.add_parser("run", help="Full pipeline: fetch → classify → report → publish → broadcast")
    p_run.add_argument("--date", default=_today())
    p_run.add_argument("--country", default="PH,ID,TH")
    p_run.add_argument("--sample", action="store_true", help="Use offline sample data")
    p_run.add_argument("--live", action="store_true", help="Use live online providers")
    p_run.add_argument("--dry-run", action="store_true", dest="dry_run", help="Skip publish step")
    p_run.add_argument("--config", default=None)

    # --- report ---
    p_rep = sub.add_parser("report", help="Fetch + classify + generate report (no publish)")
    p_rep.add_argument("--date", default=_today())
    p_rep.add_argument("--country", default="PH,ID,TH")
    p_rep.add_argument("--sample", action="store_true")
    p_rep.add_argument("--live", action="store_true")
    p_rep.add_argument("--config", default=None)

    # --- broadcast ---
    p_bc = sub.add_parser("broadcast", help="Generate broadcast text from existing report")
    p_bc.add_argument("--date", default=_today())
    p_bc.add_argument("--config", default=None)

    # --- publish ---
    p_pub = sub.add_parser("publish", help="Sync docs/ and optionally commit/push to GitHub Pages")
    p_pub.add_argument("--date", default=_today())
    p_pub.add_argument("--dry-run", action="store_true", dest="dry_run",
                       help="Print planned actions without touching git (default when no flag given)")
    p_pub.add_argument("--commit", action="store_true",
                       help="Copy files to docs/ and create a git commit")
    p_pub.add_argument("--push", action="store_true",
                       help="Same as --commit, then git push (requires --commit)")
    p_pub.add_argument("--config", default=None)

    args = parser.parse_args(argv)

    from sea_trend_insight.runner import cmd_run, cmd_report, cmd_broadcast, cmd_publish

    try:
        if args.command == "run":
            countries = [c.strip() for c in args.country.split(",")]
            if not args.sample and not args.live:
                print("Error: specify --sample or --live", file=sys.stderr)
                return 1
            result = cmd_run(
                args.date, countries,
                sample=args.sample, live=args.live,
                dry_run=args.dry_run, config_path=args.config,
            )
            if result.get("errors") and not result.get("total_items"):
                return 1
        elif args.command == "report":
            countries = [c.strip() for c in args.country.split(",")]
            if not args.sample and not args.live:
                print("Error: specify --sample or --live", file=sys.stderr)
                return 1
            cmd_report(args.date, countries, sample=args.sample, live=args.live, config_path=args.config)
        elif args.command == "broadcast":
            cmd_broadcast(args.date, config_path=args.config)
        elif args.command == "publish":
            push = getattr(args, "push", False)
            commit = getattr(args, "commit", False) or push
            dry_run = args.dry_run or (not commit and not push)
            cmd_publish(args.date, dry_run=dry_run, commit=commit, push=push, config_path=args.config)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0
