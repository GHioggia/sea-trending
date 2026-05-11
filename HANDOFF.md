# HANDOFF — sea-trend-insight 阶段交接

## 项目目标

面向游戏策划的东南亚（菲律宾/印尼/泰国）每日趋势数据抓取与洞察报告工具。抓取公开趋势数据 → 去重 → 分类 → 评分 → 分析洞察 → 生成 HTML 报告 → 发布 GitHub Pages → 输出播报文本。

## 已完成内容（第 1-5 轮）

1. **项目计划** — 实施计划、目录结构、模块职责、MVP 定义
2. **Skill 骨架** — `.claude/skills/sea-trend-insight/SKILL.md` + 5 个详细文档
3. **Sample 数据与 CLI 主流程** — 完整 pipeline：fetch → normalize → classify → report → publish → broadcast，17 个测试全通过
4. **真实数据源 provider** — 8 个 live provider 实现 + proxy 支持 + Playwright 浏览器渲染
5. **分析层** — 去重、分类改进（来源权重 + debug）、四维评分、国家/跨国/游戏热点分析、设计洞察模板、broadcast.md 格式

## 目录结构

```
sea-trending/
├── config/default.yaml              # 配置（国家、provider 开关、proxy、评分权重、分析参数）
├── data/sample/                     # 9 个离线 sample JSON（3 国 × 3 源）
├── src/sea_trend_insight/
│   ├── __main__.py / cli.py         # CLI 入口（run/report/broadcast/publish）
│   ├── models.py                    # SourceItem, NormalizedItem, ScoredItem, ScoreBreakdown,
│   │                                #   DesignInsight, CountrySummary, TrendSummary, ReportSection, RunLog
│   ├── config.py                    # 配置加载
│   ├── dedup.py                     # 三级去重（URL/keyword/title 相似度）
│   ├── classifier.py                # 分类器（来源权重 + 强/弱关键词 + debug）
│   ├── scorer.py                    # 四维评分（relevance/virality/game_design_value/risk）
│   ├── analyzer.py                  # 分析器（国家汇总/跨国热点/游戏热点/设计洞察）
│   ├── report.py                    # 报告构建 → report.json
│   ├── publisher.py                 # HTML 渲染 + 发布到 public/
│   ├── broadcast.py                 # 播报文本生成（broadcast.md）
│   ├── runner.py                    # 主编排器
│   └── providers/
│       ├── base.py                  # TrendProvider 抽象基类
│       ├── http_util.py             # 共享 HTTP session（UA/retry/timeout/proxy）
│       ├── sample.py                # 离线 sample 数据
│       ├── google_trends.py         # Google Trends RSS
│       ├── google_news.py           # Google News RSS
│       ├── gdelt.py                 # GDELT DOC API
│       ├── trends24.py              # Trends24 HTML 解析
│       ├── getdaytrends.py          # GetDayTrends HTML 解析
│       ├── kworb_youtube.py         # Kworb YouTube HTML 解析
│       ├── google_play.py           # Google Play（Playwright 浏览器渲染）
│       ├── appbrain.py              # AppBrain（disabled，403 反爬）
│       └── appfigures.py            # Appfigures（disabled，需 API key）
├── tests/
│   ├── fixtures/                    # 7 个 provider 离线 fixture
│   ├── test_sample_run.py           # 7 个端到端测试
│   ├── test_providers.py            # 11 个 provider 单元测试
│   └── test_analysis.py            # 24 个分析层测试（dedup/classifier/scorer/analyzer）
├── .claude/skills/sea-trend-insight/
│   ├── SKILL.md                     # Claude Code Skill 入口
│   └── docs/                        # workflow/config/providers/publish/acceptance/scoring
├── scripts/                         # 辅助 shell 脚本
├── pyproject.toml                   # 依赖：pyyaml, jinja2, feedparser, requests, bs4
├── README.md
└── .gitignore
```

## 关键入口文件

| 文件 | 作用 |
|------|------|
| `src/sea_trend_insight/cli.py` | CLI 参数解析，分发到 runner |
| `src/sea_trend_insight/runner.py` | 主编排器，pipeline: fetch → dedup → classify → score → analyze → report → publish → broadcast |
| `src/sea_trend_insight/dedup.py` | 去重（URL/keyword/title 相似度） |
| `src/sea_trend_insight/classifier.py` | 分类（来源权重 + 关键词 + debug） |
| `src/sea_trend_insight/scorer.py` | 四维评分（relevance/virality/game_design_value/risk） |
| `src/sea_trend_insight/analyzer.py` | 分析（国家汇总/跨国热点/设计洞察） |
| `src/sea_trend_insight/providers/__init__.py` | `LIVE_PROVIDERS` 字典，provider 注册表 |
| `config/default.yaml` | 所有配置（proxy、provider 开关、评分权重、分析参数） |

## CLI 命令

```bash
# 激活 venv
. .venv/bin/activate

# sample 离线 dry-run
python -m sea_trend_insight run --date 2026-05-09 --sample --dry-run

# live 真实数据 dry-run
python -m sea_trend_insight run --date 2026-05-11 --live --dry-run

# live 真实数据 + 发布
python -m sea_trend_insight run --date 2026-05-11 --live

# 只生成播报文本（需先有 report.json）
python -m sea_trend_insight broadcast --date 2026-05-09

# 运行测试
python -m pytest tests/ -v
```

## Pipeline 流程（第 5 轮更新）

```
fetch(sample/live) → normalize → dedup → classify(with debug)
→ score(4 dimensions) → analyze(summaries + insights)
→ build_report(report.json) → render_html → broadcast.md
```

## report.json 结构

```json
{
  "date": "2026-05-09",
  "total_items": 30,
  "items_by_country": {"PH": 10, "ID": 10, "TH": 10},
  "items_by_category": {"news": 9, "gaming": 8, "viral": 7, "trending": 6},
  "sections": [
    {
      "category": "news",
      "country": "PH",
      "items": [
        {
          "keyword": "...",
          "scores": {
            "relevance": 0.64,
            "virality": 0.31,
            "game_design_value": 0.0,
            "risk": 0.0,
            "debug": { ... }
          },
          "classify_debug": { "source": "...", "reason": "..." }
        }
      ]
    }
  ],
  "country_summaries": [...],
  "trend_summary": {
    "cross_country_hotspots": [...],
    "country_unique_hotspots": {...},
    "gaming_hotspots": [...],
    "design_insights": [
      {
        "item_keyword": "...",
        "why_notable": "...",
        "player_psychology": "...",
        "game_design_direction": "...",
        "risk_reminder": "..."
      }
    ]
  },
  "dedup_log": [...]
}
```

## 当前测试结果

**41/41 通过**（1.13s）
- test_analysis.py: 24 个分析层测试
- test_providers.py: 11 个 provider 解析/分类单元测试
- test_sample_run.py: 7 个端到端 pipeline 测试（含新 report.json 结构验证）

## 已知问题

1. **未初始化 git** — 项目目录还没有 `git init`
2. **GDELT 429 限流** — 连续请求 3 国时容易触发，可加请求间隔
3. **AppBrain 403** — 反爬机制
4. **HTML 报告样式简陋** — 功能可用但视觉上需要美化
5. **设计洞察模板固定** — 目前 6 类模板，覆盖面有限
6. **评分权重待调优** — 当前权重是初始设定，需要真实数据反馈调整

## 下一轮建议

1. **git init + 首次提交**
2. **HTML 报告美化** — 现代 dashboard 风格，展示评分、洞察
3. **GDELT 请求间隔** — 防 429
4. **评分权重调优** — 基于真实数据调整
5. **LLM 洞察增强（可选）** — 用 Claude API 替换模板生成更丰富的洞察
6. **SKILL.md 更新** — 反映分析层能力
