#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=== sea-trend-insight: 生成今日报告 ==="
echo "项目目录: $PROJECT_ROOT"
echo ""

cd "$PROJECT_ROOT"

if [ ! -f requirements.txt ]; then
    echo "[ERROR] requirements.txt 不存在，请先完成项目初始化"
    exit 1
fi

pip install -q -r requirements.txt 2>/dev/null || {
    echo "[WARN] 依赖安装失败，尝试继续..."
}

exec python src/main.py "$@"
