# 配置说明

## 命令行参数

```
python src/main.py [OPTIONS]

选项:
  --date DATE           报告日期，格式 YYYY-MM-DD（默认：今天）
  --country CODES       国家代码，逗号分隔（默认：PH,ID,TH）
  --sample              使用离线 sample 数据，不发起外部请求
  --dry-run             不执行发布步骤
  --publish             执行发布到 GitHub Pages
  --broadcast-only      只基于已有数据生成播报文本
  --output-dir DIR      输出根目录（默认：output/）
  --config FILE         配置文件路径（默认：src/config.yaml）
  --log-level LEVEL     日志级别（默认：INFO）
```

## 配置文件（src/config.yaml）

```yaml
countries:
  - PH
  - ID
  - TH

providers:
  google_trends:
    enabled: true
  google_news:
    enabled: true
  gdelt:
    enabled: false
  trends24:
    enabled: false
  getdaytrends:
    enabled: false
  youtube_trends:
    enabled: false
  appbrain:
    enabled: false
  appfigures:
    enabled: false
  tiktok:
    enabled: true
    mode: mock          # mock | apify | api

output:
  base_dir: output
  raw_dir: output/raw
  normalized_dir: output/normalized
  reports_dir: output/reports
  broadcast_dir: output/broadcast
  logs_dir: output/logs

publish:
  mode: docs            # docs | gh-pages
  docs_dir: docs
  archive_dir: archive
  auto_commit: false
  commit_message: "chore: update trend report {date}"

broadcast:
  pages_base_url: ""    # e.g. https://user.github.io/sea-trending
  max_items_per_country: 5
```

## 环境变量

| 变量 | 说明 | 优先级 |
|------|------|--------|
| `SEA_TREND_DATE` | 覆盖 `--date` | 低于命令行参数 |
| `SEA_TREND_COUNTRIES` | 覆盖 `--country` | 低于命令行参数 |
| `SEA_TREND_OUTPUT_DIR` | 覆盖 `--output-dir` | 低于命令行参数 |
| `GITHUB_PAGES_URL` | GitHub Pages 基础 URL | 用于播报文本中的链接 |

## 配置优先级

命令行参数 > 环境变量 > config.yaml > 代码默认值
