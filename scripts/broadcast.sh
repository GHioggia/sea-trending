#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=== sea-trend-insight: 生成播报文本 ==="
cd "$PROJECT_ROOT"
exec python src/main.py --broadcast-only "$@"
