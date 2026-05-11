# sea-trend-insight

东南亚每日趋势数据抓取与玩家洞察报告生成工具。

面向游戏策划，聚焦菲律宾 (PH)、印尼 (ID)、泰国 (TH) 三国，每日抓取公开趋势数据，分类整理后生成 HTML 报告并发布到 GitHub Pages。

## 功能

- **多源数据抓取**：Google Trends、Google News、GDELT、Trends24、AppBrain 等公开数据源，每个数据源为可替换 provider
- **自动分类**：将趋势数据分为「重要新闻/民生」「游戏相关」「大传播热点/梗」「民众热搜关键词」四类
- **HTML 报告**：每日生成 `YYYY-MM-DD.html`，`index.html` 指向最新报告
- **GitHub Pages 发布**：自动提交到 `docs/` 目录或 `gh-pages` 分支
- **播报文本**：生成可直接粘贴到飞书/企微群聊的摘要文本
- **dry-run 模式**：使用内置 sample 数据离线跑通全流程

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# dry-run（离线 sample 数据）
python src/main.py --dry-run

# 正式运行
python src/main.py

# 指定日期
python src/main.py --date 2026-05-09
```

## 作为 Claude Code Skill 使用

本项目是一个 Claude Code Skill（`sea-trend-insight`）。

**Skill 入口**：`.claude/skills/sea-trend-insight/SKILL.md`

在 Claude Code 会话中，以下自然语言均可触发此 Skill：

| 说法 | 对应操作 |
|------|----------|
| "生成东南亚趋势报告" | 完整流程：抓取 → 分类 → 生成 HTML → 播报 |
| "用 sample 数据跑一下趋势报告" | `--sample` 模式，不联网 |
| "dry-run 趋势报告" | `--dry-run`，生成报告但不发布 |
| "发布趋势报告到 GitHub Pages" | `--publish`，含备份和提交 |
| "生成今日播报文本" | `--broadcast-only`，只输出可粘贴文本 |
| "抓取菲律宾和泰国的趋势" | `--country PH,TH` |

### 辅助脚本

```bash
scripts/run.sh              # 完整运行（自动安装依赖）
scripts/dry-run.sh           # sample + dry-run 快速验证
scripts/publish.sh           # 发布到 GitHub Pages
scripts/broadcast.sh         # 只生成播报文本
scripts/check-env.sh         # 检查运行环境和依赖
```

### Skill 文档结构

```
.claude/skills/sea-trend-insight/
├── SKILL.md                 # 入口（使用方式、参数、输出、约束）
└── docs/
    ├── workflow.md          # 完整工作流（7 个阶段）
    ├── config.md            # 配置参数和优先级
    ├── providers.md         # 数据源 provider 详细说明
    ├── publish.md           # 发布流程和备份策略
    └── acceptance.md        # 验收标准和检查清单
```

## 数据源

| 数据源 | 状态 | 说明 |
|--------|------|------|
| Google Trends RSS | MVP | 每日热搜趋势 |
| Google News RSS | MVP | 新闻热点 |
| Sample (离线) | MVP | 内置 sample 数据 |
| TikTok | MVP (mock) | 仅接口抽象，后续接 Apify/官方 API |
| GDELT | 计划中 | 全球事件数据 |
| Trends24 | 计划中 | Twitter/X 趋势 |
| GetDayTrends | 计划中 | 每日趋势聚合 |
| YouTube (Kworb) | 计划中 | YouTube 热门 |
| AppBrain | 计划中 | Android 应用趋势 |
| Appfigures | 计划中 | 应用商店数据 |

## 约束

- 所有数据源仅使用公开可访问的入口（RSS/CSV/公开 API）
- 不做绕验证码、逆向私有接口、代理池等行为
- TikTok 第一版仅 mock provider，真实数据后续通过合规渠道接入

## 目录结构

详见 [docs/implementation-plan.md](docs/implementation-plan.md)

## 许可

Internal use.
