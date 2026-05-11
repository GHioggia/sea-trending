#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=== sea-trend-insight: Sample 数据 Dry-run ==="
cd "$PROJECT_ROOT"
exec python src/main.py --sample --dry-run "$@"
