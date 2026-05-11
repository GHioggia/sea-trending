#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=== sea-trend-insight: 环境检查 ==="
echo ""

echo "[Python]"
python3 --version 2>/dev/null || echo "  未安装"

echo ""
echo "[依赖]"
if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
    while IFS= read -r pkg; do
        pkg_name=$(echo "$pkg" | sed 's/[>=<].*//')
        if [ -n "$pkg_name" ] && [ "${pkg_name:0:1}" != "#" ]; then
            if python3 -c "import importlib; importlib.import_module('${pkg_name}')" 2>/dev/null; then
                echo "  [OK] $pkg_name"
            else
                echo "  [MISSING] $pkg_name"
            fi
        fi
    done < "$PROJECT_ROOT/requirements.txt"
else
    echo "  requirements.txt 不存在"
fi

echo ""
echo "[目录结构]"
for dir in src src/providers templates sample_data output; do
    if [ -d "$PROJECT_ROOT/$dir" ]; then
        echo "  [OK] $dir/"
    else
        echo "  [MISSING] $dir/"
    fi
done

echo ""
echo "[Sample 数据]"
sample_count=$(find "$PROJECT_ROOT/sample_data" -name "*.json" 2>/dev/null | wc -l)
echo "  JSON 文件数: $sample_count"

echo ""
echo "检查完成。"
