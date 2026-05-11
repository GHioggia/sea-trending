# FINAL_ACCEPTANCE.md

验收日期：2026-05-11

---

## 已实现功能

### 数据抓取
- Google Trends RSS（PH / ID / TH）
- Google News RSS（PH / ID / TH）
- GDELT 公开 API
- Trends24 页面抓取
- GetDayTrends 页面抓取
- YouTube Kworb 页面抓取
- Google Play（Playwright，需单独安装 browser 依赖）
- AppBrain 页面抓取
- Appfigures（官方 API，需 API Key）
- 内置 Sample Provider（离线，始终可用）

### 数据处理
- 多源数据规范化（统一 `NormalizedItem` schema）
- 标题相似度去重（可配置阈值，默认 0.7）
- 四分类分类器：新闻 / 游戏 / 热梗 / 热搜
- 三维评分：相关性 / 传播力 / 游戏设计价值 + 风险分
- 跨国共同热点分析
- 国家维度 Top-N 汇总
- 游戏设计洞察生成

### 报告生成
- Jinja2 HTML 模板（深色主题，响应式）
- 三国横向对比卡片（4 类别 × 3 国家）
- 跨国热点、风险提醒、游戏洞察模块
- Google News 条目自动构造搜索链接（`news.google.com/search?q=`）
- 数据源健康状态面板

### 发布流程
- docs/ 模式 GitHub Pages 发布
- 默认 dry-run，必须 `--commit` 才写 git
- 必须 `--push` 才推送，不会自动 push
- 发布前备份旧 `docs/index.html` 到 `archive/`
- 发布后生成 `publish-log.json` 和 `broadcast.md`

### CLI
```
python -m sea_trend_insight run      [--sample|--live] [--dry-run] [--date] [--country]
python -m sea_trend_insight report   [--sample|--live] [--date] [--country]
python -m sea_trend_insight broadcast [--date]
python -m sea_trend_insight publish  [--dry-run] [--commit] [--push] [--date]
```

### 测试
- 41 个测试全部通过（去重、分类、评分、分析、Provider 解析、端到端集成）

---

## 未实现功能

| 功能 | 说明 |
|------|------|
| TikTok 实时数据 | Provider 抽象已建好，接口层为 mock；需接入 Apify 或官方 API |
| 自动定时运行 | 无 cron/scheduler；需手动触发或在 CI/Actions 中配置 |
| 历史趋势对比 | 每日报告独立，无跨日趋势对比图表 |
| 多语言摘要 | 中文标注基于静态词典，无 LLM 翻译 |
| 移动端优化 | 响应式断点已有，但未针对手机做深度测试 |
| 用户认证数据源 | 需登录的平台（如 Sensor Tower）尚未接入 |

---

## 如何运行 sample

```bash
# 1. 安装依赖
pip install -e .

# 2. 完整 sample 流程（推荐验收时使用）
python -m sea_trend_insight run --date 2026-05-09 --sample

# 3. 查看发布计划（需要先跑步骤2）
python -m sea_trend_insight publish --date 2026-05-09 --dry-run

# 4. 跑测试
python -m pytest tests/ -v
```

输出位置：
- `reports/2026-05-09/report.json` — 结构化报告
- `reports/2026-05-09/broadcast.md` — 播报文本
- `public/2026-05-09.html` — 本地预览 HTML

---

## 如何运行 live

```bash
# 前提：能访问外网，或配置了代理
export SEA_TREND_PROXY=http://your-proxy:port   # 可选

python -m sea_trend_insight run --date $(date +%Y-%m-%d) --live
```

在 `config/default.yaml` 中按需启用/禁用各 provider：
```yaml
providers:
  google_trends:
    enabled: true
  google_play:
    enabled: true   # 需要 playwright install chromium
  appfigures:
    enabled: false
    api_key: "your-key"
```

---

## 如何配置 GitHub Pages

1. 将本项目推送到 GitHub：
   ```bash
   git remote add origin https://github.com/GHioggia/sea-trending.git
   git push -u origin main
   ```

2. 在 GitHub 仓库页面：Settings → Pages → Source → Branch: `main` / Folder: `/docs` → Save

3. 等待 1～3 分钟，Pages 站点上线：`https://GHioggia.github.io/sea-trending/`

4. 每次发布：
   ```bash
   python -m sea_trend_insight run --date YYYY-MM-DD --sample   # 或 --live
   python -m sea_trend_insight publish --date YYYY-MM-DD --commit --push
   ```

---

## 如何接入 TikTok Apify / API

项目已预留 TikTok Provider 接口（`src/sea_trend_insight/providers/`），接入步骤：

**方案 A：Apify TikTok Scraper**
```python
# 在 providers/tiktok.py 中替换 mock 实现
import requests

class TikTokProvider(TrendProvider):
    def fetch(self, country, date):
        r = requests.post(
            "https://api.apify.com/v2/acts/clockworks~tiktok-scraper/run-sync-get-dataset-items",
            params={"token": self.api_key},
            json={"searchQueries": [country], "resultsPerPage": 20}
        )
        return self._parse(r.json(), country)
```

在 `config/default.yaml` 中启用：
```yaml
providers:
  tiktok:
    enabled: true
    mode: apify
    api_key: "apify_api_xxxx"
```

**方案 B：TikTok Research API（官方）**
需申请 TikTok for Developers → Research API，接口文档：`https://developers.tiktok.com/products/research-api/`

---

## 已知限制

1. **Google Play Provider 需要 Playwright**：`pip install playwright && playwright install chromium`，环境不同可能失败，失败时自动跳过。

2. **Google News 样本 URL**：sample 数据中 google_news 条目没有具体文章 URL（已设为 null），点击跳转到 Google News 搜索结果页；实时抓取时 feedparser 会拿到真实文章链接。

3. **中文标注基于词典**：`translator.py` 使用静态词典进行中文注释，未覆盖的词汇显示为空。

4. **不支持 gh-pages 分支模式**：当前仅支持 `docs/` 目录模式；如需 `gh-pages` 分支，需要额外实现 `git_publisher.py` 中的分支推送逻辑。

5. **单 proxy**：代理配置为单一代理地址（非池），适合企业网关场景。

---

## 后续路线图

### P0（近期）
- [ ] 接入 TikTok Apify，补全热门短视频数据
- [ ] GitHub Actions 定时任务（每日 08:00 自动跑 live + publish）

### P1（中期）
- [ ] 跨日趋势对比（同一话题连续出现 → 热度曲线）
- [ ] 多语言摘要（接入 Claude API，自动生成英文/中文双语洞察）
- [ ] Slack/飞书 webhook 自动推送 broadcast.md

### P2（长期）
- [ ] 更多市场：VN（越南）、MY（马来西亚）
- [ ] 竞品游戏榜单监控（App Store + Google Play 双端）
- [ ] 话题风险自动标记（接入内容安全 API）
