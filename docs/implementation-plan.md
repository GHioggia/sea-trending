# 实施计划

## 目录结构

```
sea-trending/
├── .claude/skills/sea-trend-insight/
│   └── SKILL.md                    # Claude Code Skill 入口
├── docs/
│   ├── implementation-plan.md      # 本文档
│   ├── providers.md                # 数据源 provider 详细说明
│   └── report-format.md            # 报告格式与分类规则
├── src/
│   ├── __init__.py
│   ├── main.py                     # 主入口：编排 抓取→分类→生成→发布
│   ├── config.py                   # 配置管理
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── base.py                 # TrendProvider 抽象基类
│   │   ├── google_trends.py        # Google Trends RSS/CSV
│   │   ├── google_news.py          # Google News RSS
│   │   ├── gdelt.py                # GDELT API
│   │   ├── trends24.py             # Trends24
│   │   ├── getdaytrends.py         # GetDayTrends
│   │   ├── youtube_trends.py       # Kworb / YouTube Trends24
│   │   ├── appbrain.py             # AppBrain
│   │   ├── appfigures.py           # Appfigures
│   │   ├── tiktok_mock.py          # TikTok mock provider
│   │   └── sample.py               # 离线 sample 数据 provider
│   ├── classifier.py               # 趋势数据分类
│   ├── report.py                   # HTML 报告生成
│   ├── publisher.py                # GitHub Pages 发布
│   └── broadcast.py                # 播报文本生成
├── templates/
│   ├── daily.html                  # 每日报告 Jinja2 模板
│   └── index.html                  # 首页模板
├── sample_data/                    # 离线 sample 数据
├── output/                         # 生成产物 (gitignored)
│   ├── raw/                        # 原始抓取数据
│   ├── normalized/                 # 规范化后数据
│   └── reports/                    # 最终 HTML 报告
├── tests/
├── requirements.txt
├── README.md
└── .gitignore
```

## 统一数据模型

```python
@dataclass
class TrendItem:
    keyword: str           # 趋势关键词
    country: str           # PH / ID / TH
    source: str            # provider 名称
    category: str | None   # 分类结果（分类后填充）
    rank: int | None       # 排名（如有）
    volume: str | None     # 搜索量级描述（如有）
    url: str | None        # 原始链接
    snippet: str | None    # 摘要/描述
    fetched_at: str        # ISO 时间戳
```

## 模块职责

### providers/base.py
- 定义 `TrendProvider` 抽象基类
- 核心方法：`fetch(country: str, date: str) -> list[TrendItem]`
- 定义 `TrendItem` dataclass
- 提供 provider 注册/发现机制

### providers/*.py
- 每个数据源独立实现 `TrendProvider`
- 可通过 config 启用/禁用
- 自行处理请求异常和降级（单个 provider 失败不阻断整体流程）

### providers/sample.py
- 从 `sample_data/` 读取静态 JSON 文件
- 用于 `--dry-run` 和离线测试
- 保证无网络环境下全流程可跑通

### config.py
- 支持的国家列表：`["PH", "ID", "TH"]`
- 各 provider 启用/禁用开关
- 输出目录配置
- GitHub Pages 配置（分支名、目录路径）
- dry-run 标志
- 通过命令行参数和环境变量覆盖

### main.py
- 解析命令行参数（`--dry-run`, `--date`, `--country`, `--output-dir`）
- 按国家遍历已启用 provider，收集 TrendItem
- 保存原始数据到 `output/raw/`
- 调用 classifier 分类，保存到 `output/normalized/`
- 调用 report 生成 HTML，保存到 `output/reports/`
- 调用 publisher 发布
- 调用 broadcast 输出播报文本

### classifier.py
- 基于关键词规则将 TrendItem 分为 4 类：
  1. `news` — 重要新闻/民生
  2. `gaming` — 游戏相关
  3. `viral` — 大传播热点/梗/概念
  4. `trending` — 民众热搜关键词（默认/兜底）
- 游戏关键词库：包含主流游戏名、游戏术语、电竞赛事等
- MVP 使用纯规则，后续可接 LLM 辅助分类

### report.py
- 使用 Jinja2 渲染 HTML
- 每日报告 `YYYY-MM-DD.html`：按国家 → 按分类展示
- 首页 `index.html`：指向最新报告 + 历史列表
- 报告包含：日期、国家、分类、关键词、排名、来源链接、摘要
- 移动端友好的响应式布局

### publisher.py
- 将生成的 HTML 写入发布目录（默认 `docs/`）
- 发布前将旧 `index.html` 备份到 `archive/`
- 支持两种模式：
  1. `docs/` 目录模式（MVP，最简单）
  2. `gh-pages` 分支模式（后续）

### broadcast.py
- 生成可粘贴的纯文本播报
- 格式包含：
  - 日期
  - 各国 Top 热搜（每国 3-5 条）
  - 游戏相关趋势高亮
  - GitHub Pages 报告链接
- 输出到 stdout，同时可保存为文件

## 数据流

```
1. fetch    Provider(s) → raw JSON → output/raw/YYYY-MM-DD/{source}_{country}.json
2. normalize                      → List[TrendItem] → output/normalized/YYYY-MM-DD.json
3. classify                       → 每个 TrendItem.category 被填充
4. render                         → output/reports/YYYY-MM-DD.html + index.html
5. publish                        → docs/YYYY-MM-DD.html + docs/index.html
6. broadcast                      → stdout 播报文本
```

## MVP 范围（第一版）

### 数据源
- [x] Google Trends RSS — 三国每日趋势
- [x] Google News RSS — 三国新闻热点
- [x] Sample provider — 离线数据
- [x] TikTok mock provider — 仅接口 + 静态数据

### 功能
- [x] CLI 入口（`--dry-run`, `--date`, `--country`）
- [x] 原始数据保存（`output/raw/`）
- [x] 规范化数据保存（`output/normalized/`）
- [x] 关键词规则分类（4 类）
- [x] Jinja2 HTML 报告生成
- [x] `docs/` 目录发布模式
- [x] 播报文本生成
- [x] SKILL.md 入口

### 依赖（MVP）
- `requests` — HTTP 请求
- `feedparser` — RSS 解析
- `jinja2` — 模板渲染
- Python 标准库：`dataclasses`, `json`, `argparse`, `pathlib`, `datetime`

## 后续增强（按优先级）

### P1 — 扩充数据源
- GDELT API provider
- Trends24 provider
- GetDayTrends provider
- YouTube Kworb provider

### P2 — 功能增强
- AppBrain / Appfigures provider
- TikTok 真实数据（Apify actor 或官方 API）
- LLM 辅助分类（替代纯关键词规则）
- LLM 生成「今日洞察」总结段落
- `gh-pages` 分支发布模式

### P3 — 运营增强
- archive/ 历史归档与导航页
- 多语言报告（中/英双语）
- GitHub Actions 定时运行
- 飞书/企微 Webhook 直推播报
- 趋势对比（日 vs 日、周 vs 周）

## SKILL.md 设计

SKILL.md 保持简短，核心内容：
- **何时使用**：用户要求生成东南亚趋势报告 / 抓取 SEA 趋势数据
- **输入**：日期（可选）、国家（可选）、dry-run 标志
- **输出**：HTML 报告 + 播报文本
- **操作步骤**：运行 `python src/main.py` 并传入参数
- **验收方式**：检查 `output/reports/` 下生成的 HTML 文件，打开查看内容
