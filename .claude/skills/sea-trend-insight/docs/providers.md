# 数据源 Provider

## 架构

所有 provider 继承 `TrendProvider` 基类（`src/sea_trend_insight/providers/base.py`）：

```python
class TrendProvider(ABC):
    name: str
    platform: str

    @abstractmethod
    def fetch(self, country: str, date: str) -> list[SourceItem]: ...

    def save_raw(self, items, out_dir, country) -> Path: ...
```

共享 HTTP 工具（`providers/http_util.py`）提供：
- 可配置 User-Agent
- 自动 retry（429/5xx，指数退避）
- 统一 timeout

每个 provider 独立处理异常。runner 层 `try/except` 保证单个 provider 失败不阻断整体流程。

## Provider 状态总览

| Provider | 文件 | 状态 | Live 测试结果 |
|----------|------|------|---------------|
| Sample | `providers/sample.py` | ✅ 可用 | N/A（离线） |
| Google News RSS | `providers/google_news.py` | ✅ 已实现 | 当前环境网络不通 |
| GDELT | `providers/gdelt.py` | ✅ 已实现 | ✅ 成功（PH/ID/TH） |
| Trends24 | `providers/trends24.py` | ✅ 已实现 | ✅ 成功（PH/ID/TH 各 30 条） |
| GetDayTrends | `providers/getdaytrends.py` | ✅ 已实现 | ✅ 成功（PH/ID/TH 各 30 条） |
| Kworb YouTube | `providers/kworb_youtube.py` | ✅ 已实现 | ✅ 成功（PH/ID/TH 各 25 条） |
| AppBrain | `providers/appbrain.py` | ✅ 已实现 | 当前环境网络超时 |
| Appfigures | `providers/appfigures.py` | ⏳ 需 API key | 无 key 时自动跳过 |
| TikTok Mock | `providers/sample.py` | ✅ Sample 数据 | N/A |

## Provider 详细说明

### Google News RSS

- **文件**：`src/sea_trend_insight/providers/google_news.py`
- **URL**：`https://news.google.com/rss?hl={lang}&gl={country}&ceid={country}:{lang}`
- **国家映射**：PH → `en-PH/PH:en`, ID → `id/ID:id`, TH → `th/TH:th`
- **解析**：feedparser → 取前 25 条 → 去除标题中的 ` - Source` 后缀
- **输出**：新闻标题、链接、发布时间、摘要

### GDELT

- **文件**：`src/sea_trend_insight/providers/gdelt.py`
- **URL**：`https://api.gdeltproject.org/api/v2/doc/doc`
- **参数**：`query=sourcecountry:{Country}&mode=artlist&format=json&maxrecords=30`
- **国家映射**：PH → Philippines, ID → Indonesia, TH → Thailand
- **限制**：有 429 限流，已内置 retry；建议国家间加 1 秒间隔
- **输出**：新闻标题、URL、发布时间、来源域名

### Trends24

- **文件**：`src/sea_trend_insight/providers/trends24.py`
- **URL**：`https://trends24.in/{slug}/`（philippines/indonesia/thailand）
- **解析**：BeautifulSoup → 匹配 `li a[href*='/trend/']` → 去重
- **回退**：如果主选择器无结果，回退到 `ol li a` 等通用选择器
- **输出**：Twitter/X 趋势话题，最多 30 条

### GetDayTrends

- **文件**：`src/sea_trend_insight/providers/getdaytrends.py`
- **URL**：`https://getdaytrends.com/{slug}/`
- **解析**：BeautifulSoup → `table tr td` → 解析话题名 + 搜索量
- **搜索量解析**：支持 `200K+`、`1.5M`、纯数字等格式
- **输出**：Twitter 趋势 + 搜索量，最多 30 条

### Kworb YouTube

- **文件**：`src/sea_trend_insight/providers/kworb_youtube.py`
- **URL**：`https://kworb.net/youtube/trending/{cc}.html`（ph/id/th）
- **解析**：BeautifulSoup → `table tr td` → 视频标题 + 观看数
- **输出**：YouTube 热门视频标题 + 播放量，最多 25 条

### AppBrain

- **文件**：`src/sea_trend_insight/providers/appbrain.py`
- **URL**：`https://www.appbrain.com/stats/google-play-rankings/top_free/game/{cc}`
- **解析**：BeautifulSoup → `table tr td a` → 应用名 + 链接
- **输出**：Android 热门免费游戏 Top 20
- **注意**：自动附加 `gaming` tag，有利于分类器识别

### Appfigures

- **文件**：`src/sea_trend_insight/providers/appfigures.py`
- **需要**：API key（通过 `config/default.yaml` 的 `providers.appfigures.api_key` 配置）
- **行为**：无 API key 时返回空列表并记录 info 日志，不报错
- **后续**：配置 API key 后自动启用

### Sample Provider

- **文件**：`src/sea_trend_insight/providers/sample.py`
- **数据源**：`data/sample/{source}_{country}.json`
- **用途**：`--sample` 模式，离线跑通全流程
- **覆盖**：3 国 × 3 源 = 9 个文件，共 30 条数据，覆盖全部 4 个分类

## 添加新 Provider

1. 在 `src/sea_trend_insight/providers/` 创建新文件
2. 继承 `TrendProvider`，设置 `name` 和 `platform`，实现 `fetch()`
3. 在 `providers/__init__.py` 的 `LIVE_PROVIDERS` 字典中注册
4. 在 `config/default.yaml` 的 `providers:` 下添加配置项
5. 在 `tests/fixtures/` 添加样例响应文件
6. 在 `tests/test_providers.py` 添加 `_parse()` 单元测试

## 合规要求

- 只使用公开可访问的数据入口（RSS feed、公开 API、公开网页）
- 遵守各站点 robots.txt
- User-Agent 标识为 `sea-trend-insight/0.1`
- 内置 retry + 指数退避，不暴力重试
- 不绕过登录、验证码、反爬机制
- 不使用代理池、指纹浏览器
