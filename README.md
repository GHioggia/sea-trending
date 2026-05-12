# sea-trend-insight

东南亚每日趋势数据抓取与玩家洞察报告生成工具，面向游戏策划。

聚焦菲律宾 (PH)、印尼 (ID)、泰国 (TH) 三国，每日抓取公开趋势数据，分类整理后生成 HTML 报告并发布到 GitHub Pages。

---

## 快速开始

```bash
# 安装依赖（Python 3.11+）
pip install -e ".[dev]"

# 离线 sample 数据跑通全流程（不联网）
python -m sea_trend_insight run --date 2026-05-09 --sample

# 实时抓取并生成报告
python -m sea_trend_insight run --date 2026-05-12 --live

# 查看发布计划（dry-run，不改 git）
python -m sea_trend_insight publish --date 2026-05-12 --dry-run

# 提交 HTML 到 docs/ 并推送到 GitHub Pages
python -m sea_trend_insight publish --date 2026-05-12 --commit --push
```

---

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

---

## 数据源

共 13 个数据源，在 `config/default.yaml` 的 `providers:` 节点可随时开关。

| 数据源 | 平台类型 | 覆盖国家 | 状态 |
|--------|---------|---------|------|
| Google Trends | 搜索 | PH / ID / TH | ✅ 启用 |
| Google News | 搜索 | PH / ID / TH | ✅ 启用 |
| GDELT | 新闻 | PH / ID / TH | ✅ 启用 |
| Trends24 | Twitter 热搜 | PH / ID / TH | ✅ 启用 |
| GetDayTrends | Twitter 热搜 | PH / ID / TH | ✅ 启用 |
| Kworb YouTube | YouTube 排行 | PH / ID / TH | ✅ 启用 |
| Google Play | 应用商店 | PH / ID / TH | ✅ 启用（需 Playwright）|
| Rappler | PH 新闻网站 | 仅 PH | ✅ 启用 |
| Detik | ID 新闻网站 | 仅 ID | ✅ 启用 |
| LINE Today | TH 新闻聚合 | 仅 TH | ✅ 启用 |
| AppBrain | 应用商店 | PH / ID / TH | ❌ 关闭（待评估）|
| Appfigures | 应用商店 API | PH / ID / TH | ❌ 关闭（需 API Key）|
| TikTok | 短视频 | — | ❌ 待接入 |

所有数据源仅使用公开入口，不绕过验证码/登录，不使用代理池。

---

## 数据处理流程

抓取到的原始数据经过一条固定管道整理后生成报告：

```
fetch → normalize → dedup → classify → score → analyze → report → HTML
```

**① fetch（抓取）**
每个 provider 返回 `SourceItem` 列表（keyword、title、url、raw_score、platform、country），原始数据保存到 `data/raw/{date}/`。

**② normalize（归一化）**
统一字段格式，补充 `fetched_at` 时间戳，默认 `category = trending`。

**③ dedup（去重）**
用标题相似度（SequenceMatcher，默认阈值 0.7）合并重复条目，合并后记录 `merged_from` 来源列表。

**④ classify（分类）**
基于关键词正则 + 数据源类型，将每条记录归入四类：
- `gaming` — 游戏相关
- `news` — 新闻/民生
- `viral` — 大传播热点/梗
- `trending` — 民众热搜（兜底）

规则优先级：`google_play` 等来源强制 gaming；`gdelt`/`google_news` 来源优先 news；强匹配关键词（MLBB、Genshin 等）覆盖所有来源。关键词覆盖英语、印尼语、菲律宾语、泰语。

**⑤ score（多维评分）**
每条目计算四个 0–1 分值（`ScoreBreakdown`）：
- `relevance`：原始热度分 × 0.6 + 来源权重 × 0.4（Google Trends 最高权重 1.0）
- `virality`：平台权重（TikTok=1.0，Twitter=0.9）+ 病毒关键词加成 + 高热度加成 + 多源合并加成
- `game_design_value`：gaming 类别基础分 0.6 + 游戏/文化/传播机制关键词加成
- `risk`：敏感词命中得高分（0.7），争议词（0.4）

**⑥ analyze（分析）**
- 跨国共同热点：同一关键词出现在 ≥2 个国家
- 各国独特热点：未跨国的 Top 5
- 游戏热点 Top 10
- 设计洞察：`game_design_value ≥ 0.3` 的条目，套用 6 种模板（电竞赛事/新游发布/文化事件等）生成策划参考

**⑦ 生成报告和 HTML**
`report.json` 保存结构化数据；Jinja2 模板渲染成 HTML，按国家 × 分类分区展示，附综合统计、跨国热点、设计洞察。

---

## 发布机制与归档

### 发布流程

```
run → public/{date}.html + public/index.html（暂存，gitignore）
         ↓ publish --commit
docs/{date}.html + docs/index.html（提交到 git）
         ↓ push
GitHub Pages 自动部署（从 docs/ 目录）
```

### 是否覆盖？

- `docs/{date}.html` — **不覆盖**，每天一个新文件，永久保留，URL 形如 `https://GHioggia.github.io/sea-trending/2026-05-12.html`
- `docs/index.html` — **会覆盖**，始终指向最新一天的报告（默认首页）

### 归档机制

每次 `publish --commit` 前，旧的 `docs/index.html` 会自动备份到 `archive/index_{date}.html`，再更新新的 index。即使首页被覆盖，旧的 index 也有备份，历史日报通过固定 URL 永久访问。

### GitHub Pages 设置

1. GitHub 仓库 → Settings → Pages
2. Source: Deploy from a branch → Branch: `main` / Folder: `/docs`
3. 每次 `publish --commit --push` 后自动部署

---

## 定时任务（每日自动抓取）

### 方案 A：系统 cron

```bash
crontab -e

# 每天早上 8:00 自动抓取并发布
0 8 * * * cd /home/admin/workspace/sea-trending && python -m sea_trend_insight run --date $(date +\%Y-\%m-\%d) --live && python -m sea_trend_insight publish --date $(date +\%Y-\%m-\%d) --commit --push >> logs/cron.log 2>&1
```

### 方案 B：GitHub Actions（无需常驻服务器）

创建 `.github/workflows/daily-report.yml`：

```yaml
on:
  schedule:
    - cron: '0 0 * * *'   # UTC 00:00 = 东八区 08:00
  workflow_dispatch:
jobs:
  report:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: '3.11'}
      - run: pip install -e .
      - run: python -m sea_trend_insight run --date $(date +%Y-%m-%d) --live
      - run: python -m sea_trend_insight publish --date $(date +%Y-%m-%d) --commit --push
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

---

## 钉钉通知

播报文本（`reports/{date}/broadcast.md`）已包含跨国热点、游戏热点、各国 Top 3、设计洞察和页面链接，格式为 Markdown，可直接推送到钉钉群机器人。

接入步骤：
1. 在钉钉群创建"自定义机器人"，获取 Webhook URL
2. 在 `config/default.yaml` 添加：
   ```yaml
   notify:
     dingtalk_webhook: "https://oapi.dingtalk.com/robot/send?access_token=xxx"
   ```
3. 告诉 Claude Code "帮我接入钉钉通知"，即可自动实现推送逻辑

---

## 配置说明

`config/default.yaml` 关键字段：

```yaml
providers:
  proxy: ""                         # 可选 HTTP 代理
  google_trends:
    enabled: true
  tiktok:
    enabled: false                  # 待接入

publish:
  mode: docs
  pages_base_url: https://GHioggia.github.io/sea-trending/
  auto_push: false                  # 必须显式 --push 才推送
  backup_before_publish: true

scoring:                            # 各维度权重，可按需调整
  relevance:
    source_weights:
      google_trends: 1.0
      google_news: 0.9
```

---

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

---

## 开发

```bash
# 安装含开发依赖
pip install -e ".[dev]"

# 跑所有测试（本地 fixture，不联网）
python -m pytest tests/ -v

# 跑单个测试文件
python -m pytest tests/test_providers.py -v

# 安装 Playwright（google_play provider 需要）
pip install -e ".[browser]"
playwright install chromium
```

新增 provider 步骤：实现 `TrendProvider` 子类 → 注册到 `providers/__init__.py` 的 `LIVE_PROVIDERS` 字典 → 在 `config/default.yaml` 的 `providers:` 添加配置项。

## 项目结构

```
src/sea_trend_insight/
├── cli.py           CLI 入口
├── runner.py        子命令执行逻辑（主流程）
├── config.py        配置加载
├── models.py        数据模型（SourceItem / NormalizedItem / ScoredItem）
├── providers/       各数据源 provider
├── classifier.py    分类逻辑
├── scorer.py        多维评分
├── analyzer.py      跨国分析与设计洞察生成
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
