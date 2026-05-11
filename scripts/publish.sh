#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=== sea-trend-insight: 发布到 GitHub Pages ==="
cd "$PROJECT_ROOT"
exec python src/main.py --publish "$@"
