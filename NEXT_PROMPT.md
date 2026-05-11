# 下一轮 Prompt

将以下内容作为下一轮发给 Claude Code 的完整 prompt：

---

你在 /home/admin/workspace/sea-trending 目录下工作。这是一个东南亚每日趋势洞察报告生成项目（sea-trend-insight）。

请先阅读以下文件了解项目状态：
- HANDOFF.md（交接文档）
- PROGRESS.md（开发进度）
- config/default.yaml（当前配置）

当前状态：
- Python 包 src/sea_trend_insight/ 已完整可运行
- venv 在 .venv/，激活方式：. .venv/bin/activate
- 8 个 live provider 已实现（7 个 enabled），proxy 已配置
- 分析层已实现：去重 → 分类(debug) → 评分(4维) → 分析(洞察) → broadcast.md
- 41 个测试全部通过
- 尚未 git init

本轮任务：

1. git init + 首次提交
   - git init
   - 检查/完善 .gitignore
   - 首次 commit 包含所有当前文件

2. HTML 报告美化
   - 当前 HTML 由 publisher.py 内联模板生成，样式简陋
   - 改进方向：
     - 现代 dashboard 风格，展示评分维度
     - 分类用不同颜色/图标区分
     - 每条 item 显示来源 badge 和评分雷达
     - 展示跨国热点和设计洞察板块
     - 移动端响应式
     - 页面顶部统计摘要
   - 可以把模板拆到 templates/ 目录用 Jinja2

3. GDELT 请求间隔
   - gdelt.py 的 fetch 方法里加 1 秒 sleep
   - 或 runner.py 中遍历 provider × country 时给 GDELT 加间隔

4. 更新 SKILL.md
   - 反映分析层能力（评分、洞察、broadcast.md）
   - 反映 --live 参数和 proxy 配置
   - 更新验收方式命令

5. 运行验证
   - python -m pytest tests/ -v（全部通过）
   - python -m sea_trend_insight run --date {today} --sample --dry-run
   - 用浏览器打开生成的 HTML 确认样式

验收标准：
- [ ] git repo 已初始化，有首次 commit
- [ ] HTML 报告美观可读，展示评分和洞察
- [ ] GDELT 不再频繁 429
- [ ] SKILL.md 反映最新状态
- [ ] 41+ 测试全部通过
- [ ] sample dry-run 成功
