# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 常用命令

```bash
# 安装依赖（Python 3.11+）
pip install -e ".[dev]"

# 离线端到端跑通（不联网，使用 data/sample/ 内置数据）
python -m sea_trend_insight run --date 2026-05-09 --sample

# 实时抓取并生成报告（使用 config/default.yaml 中启用的 provider）
python -m sea_trend_insight run --date 2026-05-12 --live

# 预览发布计划（不执行 git 操作）
python -m sea_trend_insight publish --date 2026-05-12 --dry-run

# 将 HTML 提交到 docs/ 并推送到 GitHub Pages
python -m sea_trend_insight publish --date 2026-05-12 --commit --push

# 跑全部测试（使用本地 fixture 文件，不联网）
python -m pytest tests/ -v

# 只跑单个测试文件
python -m pytest tests/test_providers.py -v

# 安装 Playwright（仅 google_play provider 需要）
pip install -e ".[browser]" && playwright install chromium
```

## 架构说明

`runner.py::cmd_run` 的主流程：

```
fetch → normalize → dedup → classify → score → analyze → report → (publish) → broadcast
```

**数据模型**（`models.py`）经历三个阶段：
- `SourceItem` — provider 原始输出（keyword、title、url、raw_score、platform、country）
- `NormalizedItem` — 归一化后（补充 `fetched_at`，填入 `category`）
- `ScoredItem` — 评分后（追加 `scores: ScoreBreakdown`，含 relevance / virality / game_design_value / risk）

**Provider**（`src/providers/`）均继承 `TrendProvider`（`base.py` 抽象基类），实现 `fetch(country, date) -> list[SourceItem]`。新增 provider 步骤：实现类 → 注册到 `providers/__init__.py` 的 `LIVE_PROVIDERS` 字典 → 在 `config/default.yaml` 的 `providers:` 节点添加配置项。provider 的测试通过 `tests/fixtures/` 下的本地 HTML/JSON/XML 文件调用内部 `_parse()` 方法，不依赖网络。

`SampleProvider` 从 `data/sample/{provider}_{country}.json` 读取，始终可用于离线测试。

**分类**（`classifier.py`）将条目归入四类之一：`gaming`、`news`、`viral`、`trending`。关键词正则列表（`GAMING_KEYWORDS`、`NEWS_KEYWORDS`、`VIRAL_KEYWORDS`）覆盖英语、印尼语、菲律宾语和泰语。数据源也参与判断：`google_play` / `appbrain` / `appfigures` 强制归 `gaming`；`gdelt` / `google_news` 优先归 `news`。

**评分**（`scorer.py`）输出 0–1 的多维 `ScoreBreakdown`，权重来自 `config/default.yaml` 的 `scoring:` 节点。provider 的 `raw_score` 按 `raw_score_max` 归一化后叠加来源权重和多源加成。`game_design_value` 高 + `risk` 低的条目会进入报告的 `design_insights`。

**发布流程**（`git_publisher.py`）：
1. `run --sample/--live` 将 HTML 写入 `public/`（暂存区）
2. `publish --commit` 将 `public/{date}.html` 和 `index.html` 复制到 `docs/`，备份旧 `docs/index.html` 到 `archive/`，然后执行 `git add docs/ archive/` + `git commit`
3. `publish --push` 执行 `git push origin main`，GitHub Pages 从 `docs/` 提供服务

发布模式由 `config/default.yaml → publish.mode: docs` 控制。`public/` 目录已在 `.gitignore` 中，只有 `docs/` 会被提交。

## 配置说明

所有可调参数集中在 `config/default.yaml`：
- `providers.<name>.enabled` — 开关各个实时 provider
- `providers.proxy` — 所有 provider 请求使用的 HTTP 代理
- `publish.pages_base_url` — 用于播报文本和发布日志中的页面 URL
- `scoring.*` — 关键词加成列表和各来源权重
- `analysis.dedup.title_similarity_threshold` — 去重时标题相似度阈值（0–1）

## 输出产物（docs/ 外均被 gitignore）

| 路径 | 说明 |
|------|------|
| `reports/{date}/report.json` | 完整结构化报告（HTML 渲染的输入） |
| `reports/{date}/broadcast.md` | 格式化播报文本 |
| `public/{date}.html` | HTML 暂存（不提交） |
| `docs/{date}.html` | GitHub Pages 目标（提交） |
| `archive/index_{date}.html` | 上一版 index 备份 |
| `logs/{date}-run.log` | 运行日志 |
