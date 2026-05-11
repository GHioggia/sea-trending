# PROGRESS — sea-trend-insight 开发进度

## 第 1 轮：项目计划

- 输出实施计划 (`docs/implementation-plan.md`)
- 定义目录结构、模块职责、数据模型
- 确定 MVP 范围和后续增强优先级
- 创建 `README.md`

## 第 2 轮：Skill 骨架

- 创建 `.claude/skills/sea-trend-insight/SKILL.md`（128 行，Skill 入口）
- 拆分详细文档到 `docs/`：workflow、config、providers、publish、acceptance
- 创建 5 个辅助 shell 脚本 (`scripts/`)
- 更新 README 添加 Skill 调用说明

## 第 3 轮：Sample 数据与 CLI 主流程

- 创建 `pyproject.toml`（依赖：pyyaml, jinja2, feedparser, requests）
- 实现完整 Python 包 `src/sea_trend_insight/`：
  - 数据模型：SourceItem, NormalizedItem, ReportSection, RunLog
  - CLI：run / report / broadcast / publish 四个子命令
  - Provider 基类 + SampleProvider
  - 关键词规则分类器（4 类）
  - 报告生成（report.json + HTML）
  - GitHub Pages 发布（docs/ 模式 + 备份）
  - 播报文本生成
- 创建 9 个 sample 数据文件（3 国 × 3 源，30 条，覆盖 4 个分类）
- 创建 7 个端到端测试，全部通过
- `python -m sea_trend_insight run --date 2026-05-09 --sample --dry-run` 完整跑通

## 第 4 轮：真实数据源 Provider

- 实现 8 个 live provider：
  - Google Trends RSS（新增）
  - Google News RSS
  - GDELT DOC API
  - Trends24（HTML 解析）
  - GetDayTrends（HTML 解析）
  - Kworb YouTube（HTML 解析）
  - Google Play（Playwright 浏览器渲染）
  - AppBrain（实现但 disabled，403 反爬）
  - Appfigures（实现但 disabled，需 API key）
- 创建共享 HTTP 工具（http_util.py）：UA、retry、timeout、proxy
- 添加 `--live` CLI 参数
- 添加 proxy 支持（config + 环境变量 `SEA_TREND_PROXY`）
- 安装 Playwright + Chromium，用浏览器渲染解决 Google Play SPA 问题
- 扩充分类器关键词（泰语 เกม/ค่าไฟ、印尼语 mabar/gim、恐怖/鬼 等）
- 创建 7 个 provider fixture + 11 个单元测试
- live dry-run 验证：7 个 provider 全绿，510 条真实数据，0 错误
- 更新 providers.md 文档
- 测试：17/17 通过

## 第 5 轮：分析层 — 去重、分类改进、评分、洞察

- 创建 `dedup.py`：URL/keyword/title 相似度三级去重，排除 feed 类通用 URL
- 改进 `classifier.py`：
  - 来源直分类（google_play → gaming）
  - 强/弱游戏关键词分级
  - 新闻源优先级（gdelt/google_news 默认 news）
  - 修复 "nikkei" 误分类（`\bnikke\b` 精确匹配）
  - 新增 `classify_with_debug()` 返回分类原因
- 创建 `scorer.py`：四维评分
  - relevance_score（原始分 + 数据源权重）
  - virality_score（平台权重 + 传播关键词 + 高分 boost）
  - game_design_value_score（游戏分类 + 文化/传播机制匹配）
  - risk_score（敏感词 + 争议词检测）
  - 每个维度带 debug 字段
- 创建 `analyzer.py`：
  - 国家汇总（top items、分类计数）
  - 跨国共同热点检测（关键词相似度匹配）
  - 单国家特殊热点
  - 游戏相关热点排行
  - 设计洞察模板（6 类模板：电竞/新游/泛游戏/热梗/文化/重大新闻）
- 更新 `models.py`：新增 ScoredItem、ScoreBreakdown、DesignInsight、CountrySummary、TrendSummary
- 更新 `report.py`：report.json 新增 country_summaries、trend_summary、dedup_log
- 重写 `broadcast.py`：新 broadcast.md 格式（markdown，含跨国热点/游戏热点/设计洞察/链接占位符）
- 更新 `runner.py`：pipeline 整合 dedup → classify → score → analyze → report → broadcast
- 更新 `config/default.yaml`：新增 scoring 和 analysis 配置节点
- 创建 `docs/scoring.md`：完整评分规则文档
- 创建 `tests/test_analysis.py`：24 个新测试（dedup 7 + classifier 6 + scorer 6 + analyzer 5）
- 测试：41/41 通过（0.82s）
