# sea-trend-insight

东南亚每日趋势数据抓取与玩家洞察报告生成工具，面向游戏策划。

聚焦菲律宾 (PH)、印尼 (ID)、泰国 (TH) 三国，每日抓取公开趋势数据，分类整理后生成 HTML 报告并发布到 GitHub Pages。

## 快速开始

```bash
# 安装依赖（Python 3.11+）
pip install -e .

# 离线 sample 数据跑通全流程（不联网）
python -m sea_trend_insight run --date 2026-05-09 --sample

# 查看发布计划（dry-run，不改 git）
python -m sea_trend_insight publish --date 2026-05-09 --dry-run

# 提交 HTML 到 docs/ 并推送到 GitHub Pages
python -m sea_trend_insight publish --date 2026-05-09 --commit --push
```

## CLI 子命令

```
python -m sea_trend_insight <subcommand> [options]

子命令：
  run        完整流程：fetch → classify → score → report → publish → broadcast
  report     只生成报告，不写 public/（等同于 run --dry-run）
  broadcast  基于已有 report.json 生成播报文本
  publish    同步 docs/、git commit、可选 push

常用选项：
  --date DATE     报告日期（默认今天）
  --country LIST  国家代码，逗号分隔（默认 PH,ID,TH）
  --sample        使用内置离线 sample 数据（不联网）
  --live          使用实时 provider 抓取
  --dry-run       不执行发布步骤（run 子命令）
  --commit        同步 docs/ 并 git commit（publish 子命令）
  --push          同时执行 git push（需配合 --commit）
  --config PATH   自定义配置文件路径
```

## 输出产物

| 产物 | 路径 |
|------|------|
| 报告 JSON | `reports/{date}/report.json` |
| 播报文本 | `reports/{date}/broadcast.md` |
| 发布日志 | `reports/{date}/publish-log.json` |
| HTML（本地预览）| `public/{date}.html` |
| HTML（GitHub Pages）| `docs/{date}.html` |
| 旧页面备份 | `archive/index_{date}.html` |
| 运行日志 | `logs/{date}-run.log` |

## 配置

`config/default.yaml` — 关键字段：

```yaml
publish:
  mode: docs
  pages_base_url: https://GHioggia.github.io/sea-trending/
  auto_push: false          # 必须显式 --push 才推送
  backup_before_publish: true

providers:
  proxy: ""                 # 可选：http://your-proxy:port
  google_trends:
    enabled: true
  google_news:
    enabled: true
  tiktok:
    enabled: false          # mock 模式，待接入真实 API
```

## GitHub Pages 设置

1. GitHub 仓库 → Settings → Pages
2. Source: Deploy from a branch → Branch: `main` / Folder: `/docs`
3. 每次 `publish --commit --push` 后自动部署

## 数据源说明

| 数据源 | 类型 | 状态 |
|--------|------|------|
| Google Trends | 公开 RSS | 启用 |
| Google News | 公开 RSS | 启用 |
| GDELT | 公开 API | 启用 |
| Trends24 | 公开页面 | 启用 |
| GetDayTrends | 公开页面 | 启用 |
| YouTube Kworb | 公开页面 | 启用 |
| Google Play | Playwright 抓取 | 启用（需安装 browser 依赖）|
| AppBrain | 公开页面 | 启用 |
| Appfigures | 官方 API | 需 API Key |
| TikTok | mock / Apify | 待接入 |
| Sample | 内置离线数据 | 始终可用 |

所有数据源仅使用公开入口，不绕过验证码/登录，不使用代理池。

## 开发

```bash
# 安装含开发依赖
pip install -e ".[dev]"

# 跑测试
python -m pytest tests/ -v

# 安装 Playwright（Google Play provider 需要）
pip install -e ".[browser]"
playwright install chromium
```

## 项目结构

```
src/sea_trend_insight/
├── cli.py           CLI 入口
├── runner.py        子命令执行逻辑
├── config.py        配置加载
├── models.py        数据模型
├── providers/       各数据源 provider
├── classifier.py    分类逻辑
├── scorer.py        多维评分
├── analyzer.py      跨国分析
├── publisher.py     HTML 渲染
├── git_publisher.py GitHub Pages 发布（git 操作）
├── broadcast.py     播报文本生成
├── dedup.py         去重
└── translator.py    中文标注

config/default.yaml  默认配置
templates/           Jinja2 HTML 模板
data/sample/         离线 sample 数据
docs/                GitHub Pages 输出目录
archive/             旧页面备份
reports/             报告和日志（gitignore）
public/              本地 HTML 预览（gitignore）
```
