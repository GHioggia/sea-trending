"""GitHub Pages publishing via docs/ mode (git-backed)."""
from __future__ import annotations

import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _git(args: list[str], cwd: Path) -> tuple[int, str, str]:
    r = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


# ---------------------------------------------------------------------------
# Precondition checks
# ---------------------------------------------------------------------------

def check_preconditions(date: str, root: Path, cfg: dict) -> list[str]:
    """Return a list of error strings; empty means all good."""
    errors: list[str] = []

    public_dir = root / cfg["output"]["public_dir"]
    for name in (f"{date}.html", "index.html"):
        p = public_dir / name
        if not p.exists():
            errors.append(f"Missing required file: {p}")

    rc, _, err = _git(["rev-parse", "--git-dir"], root)
    if rc != 0:
        errors.append(
            f"Not a git repository: {root}\n"
            "  → Run: git init && git remote add origin https://github.com/GHioggia/sea-trending"
        )
        return errors  # no point checking tree state

    rc, status_out, _ = _git(["status", "--porcelain"], root)
    if rc != 0:
        errors.append("Could not read git working-tree status")

    return errors


def working_tree_summary(root: Path) -> str:
    """Return a human-readable working-tree status line."""
    rc, out, _ = _git(["status", "--short"], root)
    if rc != 0:
        return "(unknown)"
    lines = [l for l in out.splitlines() if l.strip()]
    if not lines:
        return "clean"
    return f"{len(lines)} changed file(s)"


# ---------------------------------------------------------------------------
# Dry-run plan
# ---------------------------------------------------------------------------

def dry_run_plan(date: str, root: Path, cfg: dict) -> list[str]:
    """Return ordered list of action strings that would execute on --commit."""
    pub_cfg = cfg.get("publish", {})
    backup = pub_cfg.get("backup_before_publish", True)
    pages_url = pub_cfg.get("pages_base_url", "").rstrip("/")

    public_dir = root / cfg["output"]["public_dir"]
    docs_dir = root / "docs"
    archive_dir = root / pub_cfg.get("archive_dir", "archive")

    actions: list[str] = []

    if backup:
        old_index = docs_dir / "index.html"
        if old_index.exists():
            archive_path = archive_dir / f"index_{date}.html"
            actions.append(f"BACKUP  {old_index.relative_to(root)}  →  {archive_path.relative_to(root)}")

    actions.append(f"COPY    {(public_dir / f'{date}.html').relative_to(root)}  →  {(docs_dir / f'{date}.html').relative_to(root)}")
    actions.append(f"COPY    {(public_dir / 'index.html').relative_to(root)}  →  {(docs_dir / 'index.html').relative_to(root)}")
    actions.append("GIT     git add docs/ archive/")
    actions.append(f"GIT     git commit -m 'publish: {date} SEA trend report'")
    if pages_url:
        actions.append(f"URL     {pages_url}/{date}.html")

    return actions


# ---------------------------------------------------------------------------
# Commit
# ---------------------------------------------------------------------------

def do_commit(date: str, root: Path, cfg: dict) -> dict[str, Any]:
    """Sync docs/, optionally backup, git add + commit. Returns publish log dict."""
    pub_cfg = cfg.get("publish", {})
    backup = pub_cfg.get("backup_before_publish", True)
    pages_url = pub_cfg.get("pages_base_url", "").rstrip("/")

    public_dir = root / cfg["output"]["public_dir"]
    docs_dir = root / "docs"
    archive_dir = root / pub_cfg.get("archive_dir", "archive")

    log: dict[str, Any] = {
        "date": date,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "actions": [],
        "pages_url": "",
        "errors": [],
    }

    docs_dir.mkdir(parents=True, exist_ok=True)

    if backup:
        archive_dir.mkdir(parents=True, exist_ok=True)
        old_index = docs_dir / "index.html"
        if old_index.exists():
            archive_path = archive_dir / f"index_{date}.html"
            shutil.copy2(old_index, archive_path)
            log["actions"].append(f"backup: {old_index} → {archive_path}")

    for name in (f"{date}.html", "index.html"):
        src = public_dir / name
        dst = docs_dir / name
        shutil.copy2(src, dst)
        log["actions"].append(f"copy: {src} → {dst}")

    rc, _, err = _git(["add", "docs/", str(archive_dir.relative_to(root))], root)
    if rc != 0:
        log["errors"].append(f"git add failed: {err}")
        return log
    log["actions"].append("git add docs/ archive/")

    commit_msg = f"publish: {date} SEA trend report"
    rc, out, err = _git(["commit", "-m", commit_msg], root)
    if rc != 0:
        log["errors"].append(f"git commit failed: {err}")
        return log
    log["actions"].append(f"git commit: {commit_msg}")

    rc2, sha, _ = _git(["rev-parse", "--short", "HEAD"], root)
    if rc2 == 0:
        log["commit"] = sha

    if pages_url:
        log["pages_url"] = f"{pages_url}/{date}.html"

    return log


# ---------------------------------------------------------------------------
# Push  (only called when --push is explicitly given)
# ---------------------------------------------------------------------------

def do_push(root: Path, remote: str = "origin", branch: str = "main") -> dict[str, Any]:
    """git push. Must never be called without explicit --push from caller."""
    rc, out, err = _git(["push", remote, branch], root)
    result: dict[str, Any] = {
        "action": "push",
        "remote": remote,
        "branch": branch,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "success": rc == 0,
    }
    if rc != 0:
        result["error"] = err
    else:
        result["output"] = out or err
    return result
